import pytest
from django.utils import timezone

from apps.planner.candidate_builders import build_plan_candidates
from apps.planner.candidates import CandidateKind
from apps.questions.models import Question, TechnicalQuestion
from apps.roadmaps.models import (
    Roadmap,
    RoadmapSection,
    RoadmapTopic,
    UserRoadmap,
    UserTopicProgress,
)

pytestmark = pytest.mark.django_db


def _ready_question(user, *, title, topic):
    return TechnicalQuestion.objects.create(
        owner=user,
        title=title,
        prompt="Explain the concept.",
        status=Question.Status.READY_FOR_REVIEW,
        topic=topic,
        intuition="Explain the intuition.",
    )


def _roadmap(user, topic_count=2):
    roadmap = Roadmap.objects.create(
        title="Backend Developer",
        slug="candidate-builder-backend",
        kind=Roadmap.Kind.ROLE,
    )
    section = RoadmapSection.objects.create(
        roadmap=roadmap,
        title="Databases",
        slug="databases",
    )
    topics = [
        RoadmapTopic.objects.create(
            section=section,
            title=f"Database topic {index}",
            slug=f"database-topic-{index}",
            position=index,
        )
        for index in range(1, topic_count + 1)
    ]
    UserRoadmap.objects.create(
        user=user,
        roadmap=roadmap,
        status=UserRoadmap.Status.IN_PROGRESS,
        started_at=timezone.now(),
    )
    return roadmap, topics


def test_due_reviews_become_coherent_topic_groups(user):
    now = timezone.now()
    _ready_question(
        user,
        title="Heap operations",
        topic="Heaps",
    )
    _ready_question(
        user,
        title="Heap construction",
        topic="Heaps",
    )
    _ready_question(
        user,
        title="Graph traversal",
        topic="Graphs",
    )

    build = build_plan_candidates(
        user=user,
        time_budget_minutes=60,
        plan_date=timezone.localdate(now),
        now=now,
    )
    review_candidates = [
        candidate for candidate in build.candidates if candidate.kind == CandidateKind.REVIEW
    ]

    assert len(review_candidates) == 2
    assert sum(candidate.estimated_minutes for candidate in review_candidates) == 9
    assert any("Heaps" in candidate.title for candidate in review_candidates)
    assert any("Graphs" in candidate.title for candidate in review_candidates)

def test_large_budget_only_offers_first_unfinished_roadmap_topic(user):
    now = timezone.now()
    _, topics = _roadmap(user, topic_count=8)

    build = build_plan_candidates(
        user=user,
        time_budget_minutes=720,
        plan_date=timezone.localdate(now),
        now=now,
    )

    roadmap_candidates = [
        candidate
        for candidate in build.candidates
        if candidate.kind == CandidateKind.ROADMAP
    ]

    assert len(roadmap_candidates) == 1
    assert roadmap_candidates[0].topic_ids == (topics[0].pk,)


def test_completing_first_topic_unlocks_second_topic(user):
    now = timezone.now()
    _, topics = _roadmap(user, topic_count=3)

    UserTopicProgress.objects.create(
        user=user,
        topic=topics[0],
        status=UserTopicProgress.Status.COMPLETED,
        completed_at=now,
    )

    build = build_plan_candidates(
        user=user,
        time_budget_minutes=60,
        plan_date=timezone.localdate(now),
        now=now,
    )

    roadmap_candidates = [
        candidate
        for candidate in build.candidates
        if candidate.kind == CandidateKind.ROADMAP
    ]

    assert len(roadmap_candidates) == 1
    assert roadmap_candidates[0].topic_ids == (topics[1].pk,)
