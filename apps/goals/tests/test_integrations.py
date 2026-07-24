import pytest

from apps.goals.models import InterviewGoal, InterviewStage
from apps.interviews.forms import MockInterviewCreateForm
from apps.interviews.models import MockInterview
from apps.interviews.services import create_mock_interview
from apps.planner.services import _active_roadmap_enrolment
from apps.questions.models import Question, TechnicalQuestion
from apps.roadmaps.models import Roadmap, UserRoadmap

pytestmark = pytest.mark.django_db


def test_mock_interview_form_defaults_to_primary_goal(user):
    goal = InterviewGoal.objects.create(
        user=user,
        title="Backend interview",
        goal_type=InterviewGoal.GoalType.SPECIFIC_OPPORTUNITY,
        role_title="Backend Developer",
        company="Example",
        is_primary=True,
    )
    InterviewStage.objects.create(
        goal=goal,
        stage_type=InterviewStage.StageType.TECHNICAL,
        is_current=True,
    )

    form = MockInterviewCreateForm(user=user)

    assert form.initial["goal"] == goal
    assert form.initial["focus"] == MockInterview.Focus.TECHNICAL


def test_created_mock_interview_keeps_goal_context(user):
    goal = InterviewGoal.objects.create(
        user=user,
        title="Backend interview",
        goal_type=InterviewGoal.GoalType.GENERAL_PREPARATION,
        role_title="Backend Developer",
        is_primary=True,
    )
    TechnicalQuestion.objects.create(
        owner=user,
        title="Explain HTTP caching",
        prompt="How does HTTP caching work?",
        status=Question.Status.READY_FOR_REVIEW,
        intuition="Cache reusable responses.",
    )

    interview = create_mock_interview(
        user=user,
        goal=goal,
        focus=MockInterview.Focus.TECHNICAL,
        duration_minutes=20,
    )

    assert interview.goal == goal
    assert interview.question_count == 1


def test_planner_prefers_primary_goals_linked_roadmap(user, roadmap):
    other = Roadmap.objects.create(
        title="Data Analyst",
        slug="data-analyst-goal-integration",
        kind=Roadmap.Kind.ROLE,
        is_system=True,
        is_published=True,
    )
    UserRoadmap.objects.create(
        user=user,
        roadmap=other,
        status=UserRoadmap.Status.IN_PROGRESS,
    )
    preferred = UserRoadmap.objects.create(
        user=user,
        roadmap=roadmap,
        status=UserRoadmap.Status.IN_PROGRESS,
    )
    goal = InterviewGoal.objects.create(
        user=user,
        title="Backend goal",
        goal_type=InterviewGoal.GoalType.GENERAL_PREPARATION,
        role_title="Backend Developer",
        roadmap=roadmap,
        is_primary=True,
    )

    enrolment = _active_roadmap_enrolment(user=user, goal=goal)

    assert enrolment == preferred
