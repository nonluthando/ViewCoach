from __future__ import annotations

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.text import slugify

from .models import (
    ExternalCourseRoadmap,
    Roadmap,
    RoadmapSection,
    RoadmapTopic,
    UserRoadmap,
)
from .services import roadmap_progress, sync_user_roadmap


def _next_position(queryset):
    highest = queryset.aggregate(highest=Max("position"))["highest"]
    return (highest or 0) + 1


def _unique_slug(*, queryset, title, max_length, fallback):
    base = slugify(title)[: max_length - 8] or fallback
    candidate = base
    suffix = 2
    while queryset.filter(slug=candidate).exists():
        suffix_text = f"-{suffix}"
        candidate = f"{base[: max_length - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return candidate


def custom_roadmap_cards(*, user):
    roadmaps = list(
        Roadmap.objects.filter(
            created_by=user,
            source=Roadmap.Source.CUSTOM,
            external_course__isnull=True,
            is_system=False,
            is_published=True,
        )
        .prefetch_related("sections__topics")
        .order_by("position", "title", "pk")
    )
    enrolments = {
        enrolment.roadmap_id: enrolment
        for enrolment in UserRoadmap.objects.filter(
            user=user,
            roadmap_id__in=[roadmap.pk for roadmap in roadmaps],
        )
    }

    cards = []
    for roadmap in roadmaps:
        progress = roadmap_progress(user=user, roadmap=roadmap)
        cards.append(
            {
                "roadmap": roadmap,
                "progress": progress,
                "enrolment": enrolments.get(roadmap.pk),
            }
        )
    return cards


@transaction.atomic
def create_custom_roadmap(*, user, title, description, kind):
    user_roadmaps = Roadmap.objects.filter(
        created_by=user,
        source=Roadmap.Source.CUSTOM,
        external_course__isnull=True,
    )
    slug_base = f"{title}-{user.pk}"
    roadmap = Roadmap.objects.create(
        title=title,
        slug=_unique_slug(
            queryset=Roadmap.objects.all(),
            title=slug_base,
            max_length=160,
            fallback=f"my-roadmap-{user.pk}",
        ),
        description=description,
        kind=kind,
        source=Roadmap.Source.CUSTOM,
        learning_format=Roadmap.LearningFormat.COURSE,
        position=_next_position(user_roadmaps),
        is_system=False,
        is_published=True,
        created_by=user,
    )
    UserRoadmap.objects.create(
        user=user,
        roadmap=roadmap,
        status=UserRoadmap.Status.NOT_STARTED,
        is_focused=False,
    )
    return roadmap


@transaction.atomic
def create_custom_section(*, roadmap, title, description):
    section = RoadmapSection.objects.create(
        roadmap=roadmap,
        title=title,
        slug=_unique_slug(
            queryset=RoadmapSection.objects.filter(roadmap=roadmap),
            title=title,
            max_length=160,
            fallback="module",
        ),
        description=description,
        position=_next_position(RoadmapSection.objects.filter(roadmap=roadmap)),
    )
    return section


@transaction.atomic
def create_custom_topic(
    *,
    section,
    title,
    description,
    external_url,
    estimated_minutes,
):
    topic = RoadmapTopic.objects.create(
        section=section,
        title=title,
        slug=_unique_slug(
            queryset=RoadmapTopic.objects.filter(section=section),
            title=title,
            max_length=180,
            fallback="topic",
        ),
        description=description,
        external_url=external_url,
        estimated_minutes=estimated_minutes,
        position=_next_position(RoadmapTopic.objects.filter(section=section)),
    )
    return topic


def _normalise_positions(queryset):
    items = list(queryset.select_for_update().order_by("position", "pk"))
    changed = []
    for position, item in enumerate(items, start=1):
        if item.position != position:
            item.position = position
            changed.append(item)
    if changed:
        type(changed[0]).objects.bulk_update(changed, ["position"])
    return items


def _move_item(*, queryset, item_id, direction):
    items = _normalise_positions(queryset)
    current_index = next(
        (index for index, item in enumerate(items) if item.pk == item_id),
        None,
    )
    if current_index is None:
        return False

    offset = -1 if direction == "up" else 1
    target_index = current_index + offset
    if target_index < 0 or target_index >= len(items):
        return False

    current = items[current_index]
    target = items[target_index]
    current.position, target.position = target.position, current.position
    type(current).objects.bulk_update(
        [current, target],
        ["position"],
    )
    return True


@transaction.atomic
def move_custom_section(*, roadmap, section, direction):
    if direction not in {"up", "down"}:
        raise ValueError("Choose a valid move direction.")
    if section.roadmap_id != roadmap.pk:
        raise ValueError("That module does not belong to this roadmap.")
    return _move_item(
        queryset=RoadmapSection.objects.filter(roadmap=roadmap),
        item_id=section.pk,
        direction=direction,
    )


@transaction.atomic
def move_custom_topic(*, section, topic, direction):
    if direction not in {"up", "down"}:
        raise ValueError("Choose a valid move direction.")
    if topic.section_id != section.pk:
        raise ValueError("That topic does not belong to this module.")
    return _move_item(
        queryset=RoadmapTopic.objects.filter(section=section),
        item_id=topic.pk,
        direction=direction,
    )


def _reset_empty_roadmap(*, roadmap):
    has_topics = RoadmapTopic.objects.filter(
        section__roadmap=roadmap,
    ).exists()
    if has_topics:
        return False

    UserRoadmap.objects.filter(roadmap=roadmap).update(
        status=UserRoadmap.Status.NOT_STARTED,
        is_focused=False,
        started_at=None,
        completed_at=None,
        updated_at=timezone.now(),
    )
    return True


@transaction.atomic
def delete_custom_section(*, user, section):
    roadmap = section.roadmap
    if (
        roadmap.created_by_id != user.pk
        or roadmap.source != Roadmap.Source.CUSTOM
        or ExternalCourseRoadmap.objects.filter(roadmap=roadmap).exists()
    ):
        raise ValueError("You cannot change this roadmap.")

    section.delete()
    _normalise_positions(RoadmapSection.objects.filter(roadmap=roadmap))
    if not _reset_empty_roadmap(roadmap=roadmap):
        sync_user_roadmap(user=user, roadmap=roadmap)


@transaction.atomic
def delete_custom_topic(*, user, topic):
    section = topic.section
    roadmap = section.roadmap
    if (
        roadmap.created_by_id != user.pk
        or roadmap.source != Roadmap.Source.CUSTOM
        or ExternalCourseRoadmap.objects.filter(roadmap=roadmap).exists()
    ):
        raise ValueError("You cannot change this roadmap.")

    topic.delete()
    _normalise_positions(RoadmapTopic.objects.filter(section=section))
    if not _reset_empty_roadmap(roadmap=roadmap):
        sync_user_roadmap(user=user, roadmap=roadmap)


@transaction.atomic
def set_custom_roadmap_focus(*, user, roadmap, focused):
    locked = Roadmap.objects.select_for_update().get(
        pk=roadmap.pk,
        created_by=user,
        source=Roadmap.Source.CUSTOM,
        is_system=False,
    )
    if ExternalCourseRoadmap.objects.filter(roadmap=locked).exists():
        raise ValueError("You cannot change this roadmap.")
    enrolment, _ = UserRoadmap.objects.select_for_update().get_or_create(
        user=user,
        roadmap=locked,
    )

    if focused:
        has_topics = RoadmapTopic.objects.filter(
            section__roadmap=locked,
        ).exists()
        if not has_topics:
            raise ValueError("Add at least one topic before sending this roadmap to the planner.")
        if enrolment.status == UserRoadmap.Status.COMPLETED:
            raise ValueError(
                "This roadmap is complete. Mark a topic as learning "
                "before adding it to the planner again."
            )
        enrolment.is_focused = True
        if enrolment.status == UserRoadmap.Status.NOT_STARTED:
            enrolment.status = UserRoadmap.Status.IN_PROGRESS
            enrolment.started_at = enrolment.started_at or timezone.now()
    else:
        enrolment.is_focused = False

    enrolment.save(
        update_fields=[
            "is_focused",
            "status",
            "started_at",
            "updated_at",
        ]
    )
    return enrolment
