import pytest
from django.urls import reverse

from apps.planner.models import StudyPlan
from apps.planner.services import generate_daily_plan, start_study_session

pytestmark = pytest.mark.django_db


def test_today_plan_requires_authentication(client):
    response = client.get(reverse("planner:today"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


def test_today_plan_is_generated_on_first_visit(client, user):
    client.force_login(user)

    response = client.get(reverse("planner:today"))

    assert response.status_code == 200
    assert StudyPlan.objects.filter(user=user).count() == 1
    assert "Today’s plan" in response.content.decode()


def test_user_can_rebuild_plan_for_available_time(client, user):
    client.force_login(user)

    response = client.post(
        reverse("planner:regenerate"),
        {"time_budget_hours": "8"},
    )

    assert response.status_code == 302
    plan = StudyPlan.objects.get(user=user)
    assert plan.time_budget_minutes == 480


def test_user_can_build_a_twelve_hour_plan(client, user):
    client.force_login(user)

    response = client.post(
        reverse("planner:regenerate"),
        {"time_budget_hours": "12"},
    )

    assert response.status_code == 302
    plan = StudyPlan.objects.get(user=user)
    assert plan.time_budget_minutes == 720


def test_user_cannot_toggle_someone_elses_recommendation(
    client,
    user,
    other_user,
):
    other_plan = generate_daily_plan(
        user=other_user,
        time_budget_minutes=30,
    )
    recommendation = other_plan.recommendations.order_by("pk").first()
    assert recommendation is not None
    client.force_login(user)

    response = client.post(
        reverse(
            "planner:toggle_recommendation",
            args=[recommendation.pk],
        )
    )

    assert response.status_code == 404


def test_active_session_blocks_plan_regeneration(client, user):
    plan = generate_daily_plan(user=user, time_budget_minutes=30)
    start_study_session(plan=plan)
    client.force_login(user)

    response = client.post(
        reverse("planner:regenerate"),
        {"time_budget_hours": "1.5"},
        follow=True,
    )

    plan.refresh_from_db()
    assert response.status_code == 200
    assert plan.time_budget_minutes == 30
    assert "End the active study session" in response.content.decode()


def test_dashboard_surfaces_today_plan(client, user):
    client.force_login(user)

    response = client.get(reverse("dashboard"))

    assert response.status_code == 200
    plan = StudyPlan.objects.get(user=user)
    total_count = response.context["today_plan"]["total_count"]

    assert total_count == plan.recommendations.count()
    assert plan.recommendations.filter(is_required=True).exists()
    assert reverse("planner:today") in response.content.decode()
