import pytest
from django.utils import timezone

from apps.roadmaps.models import RoadmapTopic, UserRoadmap, UserTopicProgress
from apps.roadmaps.services import roadmap_progress, sync_user_roadmap

pytestmark = pytest.mark.django_db


def test_roadmap_progress_counts_topic_states(user, roadmap, section, topic):
    second_topic = RoadmapTopic.objects.create(
        section=section,
        title="Indexes",
        slug="indexes",
        position=2,
    )
    UserTopicProgress.objects.create(
        user=user,
        topic=topic,
        status=UserTopicProgress.Status.COMPLETED,
        started_at=timezone.now(),
        completed_at=timezone.now(),
    )
    UserTopicProgress.objects.create(
        user=user,
        topic=second_topic,
        status=UserTopicProgress.Status.IN_PROGRESS,
        started_at=timezone.now(),
    )
    roadmap = roadmap.__class__.objects.prefetch_related("sections__topics").get(pk=roadmap.pk)

    summary = roadmap_progress(user=user, roadmap=roadmap)

    assert summary == {
        "total_count": 2,
        "completed_count": 1,
        "in_progress_count": 1,
        "percentage": 50,
    }


def test_sync_marks_roadmap_completed_when_all_topics_are_complete(
    user,
    roadmap,
    topic,
):
    UserTopicProgress.objects.create(
        user=user,
        topic=topic,
        status=UserTopicProgress.Status.COMPLETED,
        started_at=timezone.now(),
        completed_at=timezone.now(),
    )
    roadmap = roadmap.__class__.objects.prefetch_related("sections__topics").get(pk=roadmap.pk)

    enrolment = sync_user_roadmap(user=user, roadmap=roadmap)

    assert enrolment.status == UserRoadmap.Status.COMPLETED
    assert enrolment.started_at is not None
    assert enrolment.completed_at is not None


def test_started_roadmap_stays_active_when_topic_progress_is_reset(user, roadmap, topic):
    enrolment = UserRoadmap.objects.create(
        user=user,
        roadmap=roadmap,
        status=UserRoadmap.Status.IN_PROGRESS,
        started_at=timezone.now(),
    )
    UserTopicProgress.objects.create(
        user=user,
        topic=topic,
        status=UserTopicProgress.Status.NOT_STARTED,
    )
    roadmap = roadmap.__class__.objects.prefetch_related("sections__topics").get(pk=roadmap.pk)

    synced = sync_user_roadmap(user=user, roadmap=roadmap)

    assert synced.pk == enrolment.pk
    assert synced.status == UserRoadmap.Status.IN_PROGRESS
    assert synced.completed_at is None
