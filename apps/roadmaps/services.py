from collections import defaultdict

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .models import (
    ExternalCourseRoadmap,
    Roadmap,
    UserRoadmap,
    UserTopicProgress,
    YouTubePlaylistRoadmap,
    YouTubeRoadmapGroup,
)

MAX_FOCUSED_VIEWCOACH_ROADMAPS = 4
MAX_FAVOURITE_YOUTUBE_ROADMAPS = 5


class RoadmapSelectionLimitError(ValueError):
    pass


@transaction.atomic
def set_viewcoach_roadmap_focus(*, user, roadmap, focused: bool):
    if roadmap.source != Roadmap.Source.VIEWCOACH or not roadmap.is_system:
        raise ValueError("Only built-in ViewCoach roadmaps can be focused.")

    list(
        UserRoadmap.objects.select_for_update()
        .filter(user=user, roadmap__source=Roadmap.Source.VIEWCOACH)
        .values_list("pk", flat=True)
    )
    enrolment, _ = UserRoadmap.objects.get_or_create(
        user=user,
        roadmap=roadmap,
    )
    if focused and enrolment.status == UserRoadmap.Status.COMPLETED:
        raise ValueError(
            "Completed roadmaps cannot be focused. Mark a topic as learning first "
            "if you want to revisit the roadmap."
        )
    if focused and not enrolment.is_focused:
        focused_count = (
            UserRoadmap.objects.filter(
                user=user,
                roadmap__source=Roadmap.Source.VIEWCOACH,
                is_focused=True,
            )
            .exclude(pk=enrolment.pk)
            .count()
        )
        if focused_count >= MAX_FOCUSED_VIEWCOACH_ROADMAPS:
            raise RoadmapSelectionLimitError(
                "You already have four focused ViewCoach roadmaps. "
                "Remove one from focus before adding another."
            )
        enrolment.is_focused = True
        if enrolment.status == UserRoadmap.Status.NOT_STARTED:
            enrolment.status = UserRoadmap.Status.IN_PROGRESS
            enrolment.started_at = enrolment.started_at or timezone.now()
    elif not focused:
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


@transaction.atomic
def set_youtube_roadmap_favourite(*, user, source, favourite: bool):
    list(
        YouTubePlaylistRoadmap.objects.select_for_update()
        .filter(user=user)
        .values_list("pk", flat=True)
    )
    locked = YouTubePlaylistRoadmap.objects.select_related("roadmap").get(
        pk=source.pk,
        user=user,
        roadmap__source=Roadmap.Source.YOUTUBE,
    )
    if favourite and not locked.is_favourite:
        favourite_count = (
            YouTubePlaylistRoadmap.objects.filter(
                user=user,
                is_favourite=True,
                roadmap__source=Roadmap.Source.YOUTUBE,
            )
            .exclude(pk=locked.pk)
            .count()
        )
        if favourite_count >= MAX_FAVOURITE_YOUTUBE_ROADMAPS:
            raise RoadmapSelectionLimitError(
                "You already have five favourite YouTube roadmaps. "
                "Unfavourite one before adding another."
            )
        locked.is_favourite = True
    elif not favourite:
        locked.is_favourite = False

    locked.save(update_fields=["is_favourite", "updated_at"])
    return locked


def progress_summary_for_user(*, user, roadmap_ids=None):
    roadmap_filter = {}
    if roadmap_ids is not None:
        roadmap_filter["topic__section__roadmap_id__in"] = roadmap_ids

    rows = (
        UserTopicProgress.objects.filter(user=user, **roadmap_filter)
        .values("topic__section__roadmap_id")
        .annotate(
            in_progress_count=Count(
                "id",
                filter=Q(status=UserTopicProgress.Status.IN_PROGRESS),
            ),
            completed_count=Count(
                "id",
                filter=Q(status=UserTopicProgress.Status.COMPLETED),
            ),
        )
    )
    return {row["topic__section__roadmap_id"]: row for row in rows}


def roadmap_progress(*, user, roadmap):
    total_count = sum(len(section.topics.all()) for section in roadmap.sections.all())
    progress = progress_summary_for_user(user=user, roadmap_ids=[roadmap.pk]).get(
        roadmap.pk,
        {},
    )
    completed_count = progress.get("completed_count", 0)
    in_progress_count = progress.get("in_progress_count", 0)
    percentage = round((completed_count / total_count) * 100) if total_count else 0
    return {
        "total_count": total_count,
        "completed_count": completed_count,
        "in_progress_count": in_progress_count,
        "percentage": percentage,
    }


def sync_user_roadmap(*, user, roadmap):
    now = timezone.now()
    user_roadmap, _ = UserRoadmap.objects.get_or_create(user=user, roadmap=roadmap)
    summary = roadmap_progress(user=user, roadmap=roadmap)

    has_progress = summary["completed_count"] or summary["in_progress_count"]
    all_completed = summary["total_count"] and (
        summary["completed_count"] == summary["total_count"]
    )

    if all_completed:
        user_roadmap.status = UserRoadmap.Status.COMPLETED
        user_roadmap.started_at = user_roadmap.started_at or now
        user_roadmap.completed_at = user_roadmap.completed_at or now
        if roadmap.source == Roadmap.Source.VIEWCOACH:
            user_roadmap.is_focused = False
    elif has_progress:
        user_roadmap.status = UserRoadmap.Status.IN_PROGRESS
        user_roadmap.started_at = user_roadmap.started_at or now
        user_roadmap.completed_at = None
    elif user_roadmap.started_at:
        user_roadmap.status = UserRoadmap.Status.IN_PROGRESS
        user_roadmap.completed_at = None
    else:
        user_roadmap.status = UserRoadmap.Status.NOT_STARTED
        user_roadmap.completed_at = None

    user_roadmap.save(
        update_fields=[
            "status",
            "is_focused",
            "started_at",
            "completed_at",
            "updated_at",
        ]
    )
    return user_roadmap


def _roadmap_card_rows(*, user, roadmaps):
    roadmap_ids = [roadmap.pk for roadmap in roadmaps]
    progress_by_roadmap = progress_summary_for_user(
        user=user,
        roadmap_ids=roadmap_ids,
    )
    enrolments = {
        enrolment.roadmap_id: enrolment
        for enrolment in UserRoadmap.objects.filter(
            user=user,
            roadmap_id__in=roadmap_ids,
        )
    }

    rows = []
    for roadmap in roadmaps:
        total_count = sum(len(section.topics.all()) for section in roadmap.sections.all())
        progress = progress_by_roadmap.get(roadmap.pk, {})
        completed_count = progress.get("completed_count", 0)
        percentage = round((completed_count / total_count) * 100) if total_count else 0
        rows.append(
            {
                "roadmap": roadmap,
                "topic_count": total_count,
                "completed_count": completed_count,
                "percentage": percentage,
                "enrolment": enrolments.get(roadmap.pk),
            }
        )
    return rows


def _group_cards_by_kind(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["roadmap"].kind].append(row)

    return [
        {
            "kind": kind,
            "label": label,
            "items": grouped.get(kind, []),
        }
        for kind, label in Roadmap.Kind.choices
        if grouped.get(kind)
    ]


def grouped_roadmap_cards(*, user):
    """Return every accessible roadmap.

    Kept for compatibility with callers that deliberately need a combined
    collection. User-facing catalogues should use a source-specific service.
    """
    roadmaps = list(
        Roadmap.objects.filter(is_published=True)
        .filter(Q(is_system=True) | Q(created_by=user))
        .prefetch_related("sections__topics")
        .order_by("kind", "position", "title")
    )
    return _group_cards_by_kind(_roadmap_card_rows(user=user, roadmaps=roadmaps))


def grouped_viewcoach_roadmap_cards(*, user):
    roadmaps = list(
        Roadmap.objects.filter(
            source=Roadmap.Source.VIEWCOACH,
            is_system=True,
            is_published=True,
        )
        .prefetch_related("sections__topics")
        .order_by("kind", "position", "title")
    )
    return _group_cards_by_kind(_roadmap_card_rows(user=user, roadmaps=roadmaps))


def youtube_roadmap_cards(*, user, favourites_only=False):
    sources_query = YouTubePlaylistRoadmap.objects.filter(
        user=user,
        roadmap__source=Roadmap.Source.YOUTUBE,
        roadmap__is_published=True,
    )
    if favourites_only:
        sources_query = sources_query.filter(is_favourite=True)
    sources = list(
        sources_query.select_related("roadmap", "group")
        .prefetch_related("roadmap__sections__topics")
        .order_by("-is_favourite", "group__position", "group__name", "-updated_at", "-pk")
    )
    rows = _roadmap_card_rows(
        user=user,
        roadmaps=[source.roadmap for source in sources],
    )
    source_by_roadmap = {source.roadmap_id: source for source in sources}
    for row in rows:
        row["youtube_source"] = source_by_roadmap[row["roadmap"].pk]
    return rows


def grouped_youtube_roadmap_cards(*, user):
    rows = youtube_roadmap_cards(user=user)
    rows_by_group = defaultdict(list)
    for row in rows:
        rows_by_group[row["youtube_source"].group_id].append(row)

    groups = list(
        YouTubeRoadmapGroup.objects.filter(user=user).order_by(
            "position",
            "name",
            "pk",
        )
    )
    result = [
        {
            "group": group,
            "label": group.name,
            "items": rows_by_group.pop(group.pk, []),
        }
        for group in groups
    ]
    ungrouped = rows_by_group.pop(None, [])
    if ungrouped:
        result.append(
            {
                "group": None,
                "label": "Ungrouped",
                "items": ungrouped,
            }
        )
    return result

def course_roadmap_cards(*, user):
    sources = list(
        ExternalCourseRoadmap.objects.filter(
            user=user,
            roadmap__learning_format=Roadmap.LearningFormat.COURSE,
            roadmap__is_published=True,
        )
        .select_related("roadmap")
        .prefetch_related("roadmap__sections__topics")
        .order_by("-updated_at", "-pk")
    )
    rows = _roadmap_card_rows(
        user=user,
        roadmaps=[source.roadmap for source in sources],
    )
    source_by_roadmap = {source.roadmap_id: source for source in sources}
    for row in rows:
        row["course_source"] = source_by_roadmap[row["roadmap"].pk]
    return rows


@transaction.atomic
def set_course_roadmap_focus(*, user, source, focused):
    locked = (
        ExternalCourseRoadmap.objects.select_for_update()
        .select_related("roadmap")
        .get(pk=source.pk, user=user)
    )
    enrolment, _ = UserRoadmap.objects.get_or_create(
        user=user,
        roadmap=locked.roadmap,
    )
    enrolment.is_focused = bool(focused)
    if focused and enrolment.status == UserRoadmap.Status.NOT_STARTED:
        enrolment.status = UserRoadmap.Status.IN_PROGRESS
        enrolment.started_at = enrolment.started_at or timezone.now()
    enrolment.save(
        update_fields=[
            "is_focused",
            "status",
            "started_at",
            "updated_at",
        ]
    )
    return enrolment
