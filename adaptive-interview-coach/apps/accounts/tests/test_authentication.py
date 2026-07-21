import pytest
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_user_can_register_and_is_logged_in(client):
    response = client.post(
        reverse("signup"),
        {
            "email": "Tee@Example.COM",
            "first_name": "Tee",
            "last_name": "",
            "password1": "A-safe-test-password-123",
            "password2": "A-safe-test-password-123",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("dashboard")
    assert User.objects.filter(email="tee@example.com").exists()

    dashboard_response = client.get(reverse("dashboard"))
    assert dashboard_response.status_code == 200
    assert dashboard_response.context["user"].is_authenticated


def test_registration_rejects_email_that_only_differs_by_case(client):
    User.objects.create_user(email="tee@example.com", password="safe-test-password")

    response = client.post(
        reverse("signup"),
        {
            "email": "TEE@example.com",
            "first_name": "Another",
            "last_name": "User",
            "password1": "A-safe-test-password-123",
            "password2": "A-safe-test-password-123",
        },
    )

    assert response.status_code == 200
    assert "already exists" in response.content.decode()
    assert User.objects.count() == 1


def test_user_can_log_in_with_case_insensitive_email(client):
    User.objects.create_user(email="tee@example.com", password="safe-test-password")

    response = client.post(
        reverse("login"),
        {"username": "TEE@EXAMPLE.COM", "password": "safe-test-password"},
    )

    assert response.status_code == 302
    assert response.url == reverse("dashboard")


def test_logout_requires_post(client):
    user = User.objects.create_user(email="tee@example.com", password="safe-test-password")
    client.force_login(user)

    get_response = client.get(reverse("logout"))
    post_response = client.post(reverse("logout"))

    assert get_response.status_code == 405
    assert post_response.status_code == 302
    assert post_response.url == reverse("home")


def test_authenticated_user_cannot_open_signup(client):
    user = User.objects.create_user(email="tee@example.com", password="safe-test-password")
    client.force_login(user)

    response = client.get(reverse("signup"))

    assert response.status_code == 403
