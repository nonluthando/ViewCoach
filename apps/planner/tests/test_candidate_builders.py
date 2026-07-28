import pytest
from django.utils import timezone

from apps.planner.candidate_builders import (
    build_plan_candidates,
    recommendation_payloads_from_selection,
)
from apps.planner.candidates import CandidateKind
from apps.planner.models import StudyRecommendation
from apps.planner.selection import select_plan_candidates
from apps.questions.models import Question, TechnicalQuestion
from apps.roadmaps.models import (
    Roadmap,
    RoadmapSection,
    RoadmapTopic,
    UserRoadmap,
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
        candidate
        for candidate in build.candidates
        if candidate.kind == CandidateKind.REVIEW
    ]

    assert len(review_candidates) == 2
    assert sum(
        candidate.estimated_minutes
        for candidate in review_candidates
    ) == 9
    assert any("Heaps" in candidate.title for candidate in review_candidates)
    assert any("Graphs" in candidate.title for candidate in review_candidates)


def test_large_budget_deepens_selected_roadmap_blocks(user):
    now = timezone.now()
    _roadmap(user, topic_count=8)

    build = build_plan_candidates(
        user=user,
        time_budget_minutes=720,
        plan_date=timezone.localdate(now),
        now=now,
    )
    selection = select_plan_candidates(
        candidates=build.candidates,
        policy=build.policy,
        time_budget_minutes=720,
        use_optimiser=False,
    )
    payloads = recommendation_payloads_from_selection(
        build_result=build,
        selection_result=selection,
        time_budget_minutes=720,
    )
    roadmap_payloads = [
        payload
        for payload in payloads
        if payload["kind"] == StudyRecommendation.Kind.ROADMAP
    ]

    assert len(roadmap_payloads) == 2
    assert all(
        payload["estimated_minutes"] >= 45
        for payload in roadmap_payloads
    )
    assert any(
        payload["estimated_minutes"] > 45
        for payload in roadmap_payloads
    )
