import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_landing_page_is_public(client):
    response = client.get(reverse("home"))

    assert response.status_code == 200


def test_dashboard_requires_authentication(client):
    response = client.get(reverse("dashboard"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


def test_health_check_reports_database_is_available(client):
    response = client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
