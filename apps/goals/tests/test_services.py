from datetime import timedelta

import pytest
from django.utils import timezone

from apps.goals.models import InterviewGoal, InterviewStage
from apps.goals.services import (
    complete_stage,
    readiness_report,
    set_current_stage,
    set_goal_status,
    set_primary_goal,
    sync_goal_roadmap,
)
from apps.interviews.models import MockInterview, MockInterviewItem
from apps.questions.models import Question, TechnicalQuestion
from apps.reviews.models import ReviewState
from apps.roadmaps.models import UserRoadmap, UserTopicProgress

pytestmark = pytest.mark.django_db


def _goal(user, *, title="Backend goal", roadmap=None, primary=False):
    return InterviewGoal.objects.create(
        user=user,
        title=title,
        goal_type=InterviewGoal.GoalType.GENERAL_PREPARATION,
        role_title="Backend Developer",
        roadmap=roadmap,
        is_primary=primary,
    )


def test_setting_primary_goal_clears_previous_primary(user):
    first = _goal(user, title="First", primary=True)
    second = _goal(user, title="Second")

    set_primary_goal(goal=second)

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_primary is False
    assert second.is_primary is True


def test_pausing_primary_goal_promotes_another_active_goal(user):
    first = _goal(user, title="First", primary=True)
    second = _goal(user, title="Second")

    set_goal_status(goal=first, status=InterviewGoal.Status.PAUSED)

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_primary is False
    assert second.is_primary is True


def test_setting_current_stage_clears_previous_stage(user):
    goal = _goal(user)
    first = InterviewStage.objects.create(
        goal=goal,
        stage_type=InterviewStage.StageType.OA,
        is_current=True,
        position=1,
    )
    second = InterviewStage.objects.create(
        goal=goal,
        stage_type=InterviewStage.StageType.TECHNICAL,
        position=2,
    )

    set_current_stage(stage=second)

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_current is False
    assert second.is_current is True


def test_completing_stage_advances_to_next_stage(user):
    goal = _goal(user)
    first = InterviewStage.objects.create(
        goal=goal,
        stage_type=InterviewStage.StageType.OA,
        is_current=True,
        position=1,
    )
    second = InterviewStage.objects.create(
        goal=goal,
        stage_type=InterviewStage.StageType.TECHNICAL,
        position=2,
    )

    complete_stage(stage=first)

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.completed_at is not None
    assert second.is_current is True


def test_sync_goal_roadmap_starts_enrolment_and_copies_deadline(user, roadmap):
    goal = _goal(user, roadmap=roadmap)
    deadline = timezone.localdate() + timedelta(days=10)
    InterviewStage.objects.create(
        goal=goal,
        stage_type=InterviewStage.StageType.TECHNICAL,
        scheduled_for=deadline,
        is_current=True,
    )

    enrolment = sync_goal_roadmap(goal=goal)

    assert enrolment.status == UserRoadmap.Status.IN_PROGRESS
    assert enrolment.target_date == deadline


def test_readiness_report_explains_roadmap_coverage(user, roadmap):
    goal = _goal(user, roadmap=roadmap)
    topics = list(roadmap.sections.first().topics.all())
    UserTopicProgress.objects.create(
        user=user,
        topic=topics[0],
        status=UserTopicProgress.Status.COMPLETED,
    )
    deadline = timezone.localdate() + timedelta(days=14)
    InterviewStage.objects.create(
        goal=goal,
        stage_type=InterviewStage.StageType.TECHNICAL,
        scheduled_for=deadline,
        is_current=True,
    )

    report = readiness_report(goal=goal)

    assert report["components"]["roadmap"]["score"] == 33
    assert report["topics_remaining"] == 2
    assert report["topics_per_week"] == 1
    assert report["days_remaining"] == 14


def test_readiness_review_health_uses_overdue_ratio(user):
    goal = _goal(user)
    question = TechnicalQuestion.objects.create(
        owner=user,
        title="Explain heaps",
        prompt="Explain a heap.",
        status=Question.Status.READY_FOR_REVIEW,
        intuition="A complete tree with an ordering property.",
    )
    ReviewState.objects.create(
        user=user,
        question=question,
        due_at=timezone.now() - timedelta(days=1),
    )

    report = readiness_report(goal=goal)

    assert report["components"]["reviews"]["score"] == 0
    assert report["components"]["reviews"]["due"] == 1


def test_readiness_uses_goal_linked_mock_interviews(user):
    goal = _goal(user)
    interview = MockInterview.objects.create(
        user=user,
        goal=goal,
        focus=MockInterview.Focus.TECHNICAL,
        duration_minutes=20,
        question_count=1,
        status=MockInterview.Status.COMPLETED,
        started_at=timezone.now() - timedelta(minutes=10),
        completed_at=timezone.now(),
    )
    MockInterviewItem.objects.create(
        interview=interview,
        position=1,
        question_title="Question",
        prompt_snapshot="Prompt",
        question_type=Question.Type.TECHNICAL,
        assessment=MockInterviewItem.Assessment.CONFIDENT,
        answered_at=timezone.now(),
    )

    report = readiness_report(goal=goal)

    assert report["components"]["mocks"]["score"] == 100
