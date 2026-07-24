from datetime import date

import pytest
from django.core.exceptions import ValidationError

from apps.goals.models import InterviewGoal, InterviewStage

pytestmark = pytest.mark.django_db


def test_specific_opportunity_requires_company(user):
    goal = InterviewGoal(
        user=user,
        title="Backend interview",
        goal_type=InterviewGoal.GoalType.SPECIFIC_OPPORTUNITY,
        role_title="Backend Developer",
    )

    with pytest.raises(ValidationError):
        goal.full_clean()


def test_current_stage_prefers_explicit_current_stage(user):
    goal = InterviewGoal.objects.create(
        user=user,
        title="Graduate role",
        goal_type=InterviewGoal.GoalType.SPECIFIC_OPPORTUNITY,
        role_title="Software Engineer",
        company="Example",
    )
    InterviewStage.objects.create(
        goal=goal,
        stage_type=InterviewStage.StageType.OA,
        scheduled_for=date(2026, 8, 1),
        position=1,
    )
    technical = InterviewStage.objects.create(
        goal=goal,
        stage_type=InterviewStage.StageType.TECHNICAL,
        scheduled_for=date(2026, 8, 7),
        position=2,
        is_current=True,
    )

    assert goal.current_stage == technical
    assert goal.next_deadline == date(2026, 8, 7)


def test_custom_stage_requires_label(user):
    goal = InterviewGoal.objects.create(
        user=user,
        title="Custom process",
        goal_type=InterviewGoal.GoalType.GENERAL_PREPARATION,
        role_title="Engineer",
    )
    stage = InterviewStage(
        goal=goal,
        stage_type=InterviewStage.StageType.CUSTOM,
    )

    with pytest.raises(ValidationError):
        stage.full_clean()
