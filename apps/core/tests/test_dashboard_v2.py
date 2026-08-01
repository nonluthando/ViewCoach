import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_dashboard_v2_renders_without_optional_user_data(client):
    user = get_user_model().objects.create_user(
        email="dashboard-v2@example.com",
        password="safe-test-password",
    )
    client.force_login(user)

    response = client.get(reverse("dashboard"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Welcome back" in content
    assert "Your study plan" in content
    assert "ViewCoach roadmaps" in content
    assert "YouTube roadmaps" in content
    assert "Set your target" in content
