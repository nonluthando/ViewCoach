import pytest
from django.urls import reverse

from apps.goals.models import InterviewGoal, InterviewStage

pytestmark = pytest.mark.django_db


def _goal(user, *, title="Backend goal"):
    return InterviewGoal.objects.create(
        user=user,
        title=title,
        goal_type=InterviewGoal.GoalType.GENERAL_PREPARATION,
        role_title="Backend Developer",
    )


def test_goal_list_requires_authentication(client):
    response = client.get(reverse("goals:list"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


def test_first_created_goal_becomes_primary(client, user, roadmap):
    client.force_login(user)

    response = client.post(
        reverse("goals:create"),
        {
            "title": "Backend preparation",
            "goal_type": InterviewGoal.GoalType.GENERAL_PREPARATION,
            "role_title": "Backend Developer",
            "company": "",
            "roadmap": roadmap.pk,
            "weekly_minutes": 300,
        },
    )

    goal = InterviewGoal.objects.get(user=user)
    assert response.status_code == 302
    assert goal.is_primary is True
    assert goal.roadmap == roadmap


def test_user_cannot_open_someone_elses_goal(client, user, other_user):
    other_goal = _goal(other_user)
    client.force_login(user)

    response = client.get(reverse("goals:detail", args=[other_goal.pk]))

    assert response.status_code == 404


def test_user_can_add_current_interview_stage(client, user):
    goal = _goal(user)
    client.force_login(user)

    response = client.post(
        reverse("goals:stage_add", args=[goal.pk]),
        {
            "stage_type": InterviewStage.StageType.TECHNICAL,
            "custom_label": "",
            "scheduled_for": "2026-08-20",
            "is_current": "on",
        },
    )

    stage = goal.stages.get()
    assert response.status_code == 302
    assert stage.is_current is True


def test_user_can_switch_primary_goal(client, user):
    first = _goal(user, title="First")
    first.is_primary = True
    first.save(update_fields=["is_primary"])
    second = _goal(user, title="Second")
    client.force_login(user)

    response = client.post(reverse("goals:set_primary", args=[second.pk]))

    first.refresh_from_db()
    second.refresh_from_db()
    assert response.status_code == 302
    assert first.is_primary is False
    assert second.is_primary is True


def test_dashboard_surfaces_primary_goal(client, user):
    goal = _goal(user, title="Backend readiness")
    goal.is_primary = True
    goal.save(update_fields=["is_primary"])
    client.force_login(user)

    response = client.get(reverse("dashboard"))

    assert response.status_code == 200
    assert response.context["primary_goal"] == goal
    assert "Backend readiness" in response.content.decode()
