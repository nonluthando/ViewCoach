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


def _ready_question(user, title="Explain heaps", topic="Heaps"):
    return TechnicalQuestion.objects.create(
        owner=user,
        title=title,
        prompt="Explain the data structure and its trade-offs.",
        status=Question.Status.READY_FOR_REVIEW,
        topic=topic,
        intuition="Keep the highest-priority value at the root.",
    )


def _active_roadmap(user, suffix="", *, focused=True):
    title = "Backend Developer" if not suffix else f"Backend Developer {suffix}"
    slug_suffix = f"-{suffix}" if suffix else ""
    roadmap = Roadmap.objects.create(
        title=title,
        slug=f"backend-developer-test{slug_suffix}",
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
        is_focused=focused,
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
    assert first.question_id == question.pk
    assert first.priority_score == 100
    assert plan_summary(plan=plan)["estimated_minutes"] <= 30


def test_short_budget_with_due_reviews_stays_review_only(user):
    now = timezone.now()
    _ready_question(user)
    TechnicalQuestion.objects.create(
        is_system=True,
        system_key="short-budget-practice",
        title="Two Sum",
        prompt="Return matching indices.",
        topic="Arrays",
    )
    _active_roadmap(user)

    plan = generate_daily_plan(
        user=user,
        time_budget_minutes=20,
        now=now,
    )

    kinds = set(plan.recommendations.values_list("kind", flat=True))
    assert kinds == {StudyRecommendation.Kind.REVIEW}


def test_due_reviews_are_grouped_by_topic(user):
    now = timezone.now()
    _ready_question(user, title="Heap operations", topic="Heaps")
    _ready_question(user, title="Heap construction", topic="Heaps")
    _ready_question(user, title="Graph traversal", topic="Graphs")

    plan = generate_daily_plan(
        user=user,
        time_budget_minutes=60,
        now=now,
    )

    review_recommendations = list(plan.recommendations.filter(kind=StudyRecommendation.Kind.REVIEW))
    assert len(review_recommendations) == 2
    review_titles = {item.title for item in review_recommendations}
    assert any("Heaps" in title for title in review_titles)
    assert any("Graphs" in title for title in review_titles)
    assert sum(item.estimated_minutes for item in review_recommendations) == 9


def test_plan_continues_next_active_roadmap_topic(user):
    _, first_topic, _ = _active_roadmap(user)

    plan = generate_daily_plan(user=user, time_budget_minutes=60)

    recommendation = plan.recommendations.get(kind=StudyRecommendation.Kind.ROADMAP)
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

    plan = generate_daily_plan(user=user, time_budget_minutes=60)

    recommendation = plan.recommendations.get(kind=StudyRecommendation.Kind.ROADMAP)
    assert recommendation.topic == second_topic


def test_large_budget_keeps_one_topic_and_deepens_its_block(user):
    roadmap, first_topic, _ = _active_roadmap(user)
    section = roadmap.sections.get()
    for position in range(3, 9):
        RoadmapTopic.objects.create(
            section=section,
            title=f"Backend topic {position}",
            slug=f"backend-topic-{position}",
            position=position,
        )

    plan = generate_daily_plan(user=user, time_budget_minutes=720)

    roadmap_recommendations = list(
        plan.recommendations.filter(kind=StudyRecommendation.Kind.ROADMAP)
    )

    assert len(roadmap_recommendations) == 1
    assert roadmap_recommendations[0].topic == first_topic
    assert roadmap_recommendations[0].estimated_minutes > 45
    assert plan.time_budget_minutes == 720
    assert plan_summary(plan=plan)["estimated_minutes"] <= 720


def test_large_budget_selects_at_most_four_roadmaps(user):
    for index in range(5):
        _active_roadmap(
            user,
            suffix=str(index),
            focused=index < 4,
        )

    plan = generate_daily_plan(user=user, time_budget_minutes=720)
    roadmap_recommendations = list(
        plan.recommendations.filter(kind=StudyRecommendation.Kind.ROADMAP).select_related(
            "topic__section__roadmap"
        )
    )
    roadmap_ids = {
        recommendation.topic.section.roadmap_id for recommendation in roadmap_recommendations
    }
    topic_count_by_roadmap = {
        roadmap_id: sum(
            recommendation.topic.section.roadmap_id == roadmap_id
            for recommendation in roadmap_recommendations
        )
        for roadmap_id in roadmap_ids
    }

    assert len(roadmap_ids) == 4
    assert all(count <= 2 for count in topic_count_by_roadmap.values())
    assert all(recommendation.estimated_minutes >= 45 for recommendation in roadmap_recommendations)


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

    recommendation = plan.recommendations.get(kind=StudyRecommendation.Kind.WEAK_AREA)
    assert recommendation.question_id == question.pk
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

    recommendation = plan.recommendations.get(kind=StudyRecommendation.Kind.PRACTICE)
    assert recommendation.question_id == question.pk


def test_empty_account_gets_question_library_starting_task(user):
    plan = generate_daily_plan(user=user, time_budget_minutes=30)

    recommendation = plan.recommendations.get()
    assert recommendation.kind == StudyRecommendation.Kind.LIBRARY
    assert recommendation.title == "Add one interview question"


def test_force_regeneration_replaces_recommendations_and_budget(user):
    first_plan = generate_daily_plan(user=user, time_budget_minutes=30)
    first_recommendation_ids = set(first_plan.recommendations.values_list("pk", flat=True))

    regenerated = generate_daily_plan(
        user=user,
        time_budget_minutes=90,
        force=True,
    )
    regenerated_ids = set(regenerated.recommendations.values_list("pk", flat=True))

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
