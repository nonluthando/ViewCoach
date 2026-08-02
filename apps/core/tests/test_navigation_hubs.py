import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("url_name", ["learn", "prepare", "interview"])
def test_section_hubs_require_authentication(client, url_name):
    response = client.get(reverse(url_name))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


@pytest.mark.parametrize(
    ("url_name", "heading", "linked_route"),
    [
        ("learn", "Build knowledge with structure.", "roadmaps:list"),
        ("prepare", "Turn knowledge into interview-ready answers.", "questions:list"),
        ("interview", "Prepare for the actual process.", "goals:list"),
    ],
)
def test_section_hubs_expose_clear_next_actions(
    client,
    user,
    url_name,
    heading,
    linked_route,
):
    client.force_login(user)

    response = client.get(reverse(url_name))
    html = response.content.decode()

    assert response.status_code == 200
    assert heading in html
    assert f'href="{reverse(linked_route)}"' in html


def test_authenticated_navigation_uses_four_user_intent_sections(client, user):
    client.force_login(user)

    response = client.get(reverse("dashboard"))
    html = response.content.decode()

    assert response.status_code == 200
    assert html.count('class="mobile-nav-link') == 4
    assert "<span>Today</span>" in html
    assert "<span>Learn</span>" in html
    assert "<span>Prepare</span>" in html
    assert "<span>Interview</span>" in html
    assert "<span>More</span>" not in html
    assert "<span>Review</span>" not in html


def test_account_menu_contains_secondary_actions(client, user):
    client.force_login(user)

    response = client.get(reverse("learn"))
    html = response.content.decode()

    assert response.status_code == 200
    assert "Open account menu" in html
    assert f'href="{reverse("questions:import_history")}"' in html
    assert "Help centre" in html
    assert "Log out" in html
