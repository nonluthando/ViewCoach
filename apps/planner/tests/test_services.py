from datetime import timedelta

import pytest
from django.utils import timezone

from apps.planner.models import StudyPlan, StudyRecommendation
from apps.planner.services import (
    finish_study_session,
    generate_daily_plan,
    plan_summary,
    start_study_session,
    toggle_recommendation_completion,
)
from apps.questions.models import Question, TechnicalQuestion
from apps.reviews.models import ReviewState
from apps.reviews.services import record_review
from apps.roadmaps.models import (
    Roadmap,
    RoadmapSection,
    RoadmapTopic,
    UserRoadmap,
    UserTopicProgress,
)

pytestmark = pytest.mark.django_db


def _ready_question(user, title="Explain heaps"):
    return TechnicalQuestion.objects.create(
        owner=user,
        title=title,
        prompt="Explain the data structure and its trade-offs.",
        status=Question.Status.READY_FOR_REVIEW,
        topic="Heaps",
        intuition="Keep the highest-priority value at the root.",
    )


def _active_roadmap(user):
    roadmap = Roadmap.objects.create(
        title="Backend Developer",
        slug="backend-developer-test",
        kind=Roadmap.Kind.ROLE,
        position=1,
    )
    section = RoadmapSection.objects.create(
        roadmap=roadmap,
        title="Databases",
        slug="databases",
        position=1,
    )
    first_topic = RoadmapTopic.objects.create(
        section=section,
        title="SQL fundamentals",
        slug="sql-fundamentals",
        position=1,
    )
    second_topic = RoadmapTopic.objects.create(
        section=section,
        title="PostgreSQL indexing",
        slug="postgresql-indexing",
        position=2,
    )
    UserRoadmap.objects.create(
        user=user,
        roadmap=roadmap,
        status=UserRoadmap.Status.IN_PROGRESS,
        started_at=timezone.now(),
    )
    return roadmap, first_topic, second_topic


def test_due_reviews_receive_highest_priority(user):
    now = timezone.now()
    question = _ready_question(user)

    plan = generate_daily_plan(
        user=user,
        time_budget_minutes=30,
        now=now,
    )

    first = plan.recommendations.first()
    assert first.kind == StudyRecommendation.Kind.REVIEW
    assert first.question_id == question.id
    assert first.priority_score == 100
    assert plan_summary(plan=plan)["estimated_minutes"] <= 30


def test_plan_continues_next_active_roadmap_topic(user):
    _, first_topic, _ = _active_roadmap(user)

    plan = generate_daily_plan(user=user, time_budget_minutes=30)

    recommendation = plan.recommendations.get(
        kind=StudyRecommendation.Kind.ROADMAP
    )
    assert recommendation.topic == first_topic
    assert "Backend Developer" in recommendation.description


def test_completed_roadmap_topic_is_skipped(user):
    _, first_topic, second_topic = _active_roadmap(user)
    UserTopicProgress.objects.create(
        user=user,
        topic=first_topic,
        status=UserTopicProgress.Status.COMPLETED,
        started_at=timezone.now(),
        completed_at=timezone.now(),
    )

    plan = generate_daily_plan(user=user, time_budget_minutes=30)

    recommendation = plan.recommendations.get(
        kind=StudyRecommendation.Kind.ROADMAP
    )
    assert recommendation.topic == second_topic


def test_recent_hard_review_becomes_weak_area_recommendation(user):
    now = timezone.now()
    question = _ready_question(user)
    state = ReviewState.objects.create(
        user=user,
        question=question,
        due_at=now,
    )
    record_review(
        state=state,
        rating="HARD",
        now=now,
    )

    plan = generate_daily_plan(
        user=user,
        time_budget_minutes=30,
        now=now + timedelta(minutes=1),
    )

    recommendation = plan.recommendations.get(
        kind=StudyRecommendation.Kind.WEAK_AREA
    )
    assert recommendation.question_id == question.id
    assert "Hard" in recommendation.rationale


def test_fresh_built_in_question_is_used_for_practice(user):
    question = TechnicalQuestion.objects.create(
        is_system=True,
        system_key="technical-test-practice-question",
        title="Two Sum",
        prompt="Return the indices that add to the target.",
        topic="Arrays and hashing",
        pattern="Hash map complement lookup",
    )

    plan = generate_daily_plan(user=user, time_budget_minutes=30)

    recommendation = plan.recommendations.get(
        kind=StudyRecommendation.Kind.PRACTICE
    )
    assert recommendation.question_id == question.id


def test_empty_account_gets_question_library_starting_task(user):
    plan = generate_daily_plan(user=user, time_budget_minutes=30)

    recommendation = plan.recommendations.get()
    assert recommendation.kind == StudyRecommendation.Kind.LIBRARY
    assert recommendation.title == "Add one interview question"


def test_force_regeneration_replaces_recommendations_and_budget(user):
    first_plan = generate_daily_plan(user=user, time_budget_minutes=30)
    first_recommendation_ids = set(
        first_plan.recommendations.values_list("pk", flat=True)
    )

    regenerated = generate_daily_plan(
        user=user,
        time_budget_minutes=90,
        force=True,
    )
    regenerated_ids = set(
        regenerated.recommendations.values_list("pk", flat=True)
    )

    assert regenerated.pk == first_plan.pk
    assert regenerated.time_budget_minutes == 90
    assert first_recommendation_ids.isdisjoint(regenerated_ids)


def test_toggling_all_recommendations_completes_plan(user):
    plan = generate_daily_plan(user=user, time_budget_minutes=30)
    recommendation = plan.recommendations.get()

    updated = toggle_recommendation_completion(
        recommendation=recommendation,
    )
    plan.refresh_from_db()

    assert updated.completed_at is not None
    assert plan.status == StudyPlan.Status.COMPLETED

    toggle_recommendation_completion(recommendation=updated)
    plan.refresh_from_db()
    assert plan.status == StudyPlan.Status.ACTIVE


def test_study_session_start_is_idempotent_and_finish_records_progress(user):
    plan = generate_daily_plan(user=user, time_budget_minutes=30)
    recommendation = plan.recommendations.get()
    toggle_recommendation_completion(recommendation=recommendation)

    first_session, created = start_study_session(plan=plan)
    repeated_session, repeated_created = start_study_session(plan=plan)
    finished = finish_study_session(session=first_session)

    assert created is True
    assert repeated_created is False
    assert repeated_session == first_session
    assert finished.ended_at is not None
    assert finished.completed_recommendation_count == 1
