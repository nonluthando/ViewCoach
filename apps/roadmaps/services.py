from collections import defaultdict

from django.db.models import Count, Q
from django.utils import timezone

from .models import Roadmap, UserRoadmap, UserTopicProgress


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
        update_fields=["status", "started_at", "completed_at", "updated_at"]
    )
    return user_roadmap


def grouped_roadmap_cards(*, user):
    roadmaps = list(
        Roadmap.objects.filter(is_published=True)
        .filter(Q(is_system=True) | Q(created_by=user))
        .prefetch_related("sections__topics")
        .order_by("kind", "position", "title")
    )
    progress_by_roadmap = progress_summary_for_user(
        user=user,
        roadmap_ids=[roadmap.pk for roadmap in roadmaps],
    )
    enrolments = {
        enrolment.roadmap_id: enrolment
        for enrolment in UserRoadmap.objects.filter(
            user=user,
            roadmap_id__in=[roadmap.pk for roadmap in roadmaps],
        )
    }

    grouped = defaultdict(list)
    for roadmap in roadmaps:
        total_count = sum(len(section.topics.all()) for section in roadmap.sections.all())
        progress = progress_by_roadmap.get(roadmap.pk, {})
        completed_count = progress.get("completed_count", 0)
        percentage = round((completed_count / total_count) * 100) if total_count else 0
        grouped[roadmap.kind].append(
            {
                "roadmap": roadmap,
                "topic_count": total_count,
                "completed_count": completed_count,
                "percentage": percentage,
                "enrolment": enrolments.get(roadmap.pk),
            }
        )

    return [
        {
            "kind": kind,
            "label": label,
            "items": grouped.get(kind, []),
        }
        for kind, label in Roadmap.Kind.choices
        if grouped.get(kind)
    ]
