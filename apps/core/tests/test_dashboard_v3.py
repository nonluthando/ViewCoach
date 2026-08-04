import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_dashboard_v3_renders_without_optional_user_data(client):
    user = get_user_model().objects.create_user(
        email="dashboard-v3@example.com",
        password="safe-test-password",
    )
    client.force_login(user)

    response = client.get(reverse("dashboard"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "dashboard-v3" in content
    assert "Build skills, practise recall" in content
    assert "Continue preparing" in content
    assert "Your focused roadmaps" in content
    assert "Your learning journey" in content
    assert "Today’s plan" in content
    assert "Evidence Bag" in content
    assert "Interview readiness" in content


def test_dashboard_v3_calendar_accepts_valid_month_and_rejects_invalid_month(client):
    user = get_user_model().objects.create_user(
        email="dashboard-calendar@example.com",
        password="safe-test-password",
    )
    client.force_login(user)

    august = client.get(reverse("dashboard"), {"month": "2026-08"})
    invalid = client.get(reverse("dashboard"), {"month": "not-a-month"})

    assert august.status_code == 200
    assert "August 2026" in august.content.decode()
    assert invalid.status_code == 200


@override_settings(
    PORTFOLIO_DEMO_ENABLED=True,
    PORTFOLIO_DEMO_SESSION_SECONDS=7200,
    PORTFOLIO_DEMO_MAX_ACTIVE=25,
)
def test_demo_dashboard_is_populated_with_real_product_data(client):
    start = client.post(reverse("portfolio_demo_start"))
    response = client.get(reverse("dashboard"))
    content = response.content.decode()

    assert start.status_code == 302
    assert response.status_code == 200
    assert "Backend and AI Interview Sprint" in content
    assert "Demo" in content
    assert "Evidence Bag" in content
    assert "Interview readiness" in content
    assert response.context["today_plan"]["completed_count"] == 1
    assert len(response.context["focused_roadmaps"]) == 2
    assert response.context["streak"]["current"] >= 4
