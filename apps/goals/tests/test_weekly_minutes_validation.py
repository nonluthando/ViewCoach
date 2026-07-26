import pytest
from django.core.exceptions import ValidationError

from apps.goals.forms import InterviewGoalForm
from apps.goals.models import InterviewGoal

pytestmark = pytest.mark.django_db


def goal_data(weekly_minutes):
    return {
        "title": "Backend interview preparation",
        "goal_type": InterviewGoal.GoalType.GENERAL_PREPARATION,
        "role_title": "Backend developer",
        "company": "",
        "weekly_minutes": weekly_minutes,
    }


def test_goal_form_accepts_4000_weekly_minutes(user):
    form = InterviewGoalForm(data=goal_data(4000), user=user)

    assert form.is_valid(), form.errors


def test_goal_form_rejects_time_above_6300_with_helpful_message(user):
    form = InterviewGoalForm(data=goal_data(6301), user=user)

    assert not form.is_valid()
    assert form.errors["weekly_minutes"] == [
        "Weekly study time cannot exceed 6300 minutes (105 hours)."
    ]


def test_weekly_minutes_field_explains_units_and_constraints(user):
    form = InterviewGoalForm(user=user)
    field = form.fields["weekly_minutes"]

    assert "600 minutes = 10 hours" in field.help_text
    assert field.widget.attrs["min"] == 0
    assert field.widget.attrs["max"] == 6300
    assert field.widget.attrs["step"] == 1


def test_goal_model_rejects_time_above_weekly_limit(user):
    goal = InterviewGoal(
        user=user,
        title="Backend interview preparation",
        goal_type=InterviewGoal.GoalType.GENERAL_PREPARATION,
        role_title="Backend developer",
        weekly_minutes=6301,
    )

    with pytest.raises(ValidationError) as exc_info:
        goal.full_clean()

    assert (
        "Weekly study time cannot exceed 6300 minutes (105 hours)."
        in exc_info.value.message_dict["weekly_minutes"]
    )
