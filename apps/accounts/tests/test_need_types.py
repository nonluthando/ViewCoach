import pytest
from django.urls import reverse

from apps.accounts.forms import NeedTypePreferencesForm
from apps.accounts.models import User
from apps.accounts.needs import need_alignment_for_kind

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("need_type", "destination"),
    [
        (User.NeedType.LEARN_ORGANISE, "roadmaps:list"),
        (User.NeedType.PRACTISE_RETAIN, "questions:import_start"),
        (User.NeedType.INTERVIEW_SKILLS, "interview"),
    ],
)
def test_signup_routes_user_to_primary_need_hub(
    client,
    need_type,
    destination,
):
    response = client.post(
        reverse("signup"),
        {
            "email": f"{need_type.lower()}@example.com",
            "first_name": "Tee",
            "last_name": "",
            "primary_need_type": need_type,
            "secondary_need_type": "",
            "password1": "A-safe-test-password-123",
            "password2": "A-safe-test-password-123",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse(destination)


def test_user_can_update_primary_and_secondary_aims(client, user):
    client.force_login(user)

    response = client.post(
        reverse("need_type_preferences"),
        {
            "primary_need_type": User.NeedType.INTERVIEW_SKILLS,
            "secondary_need_type": User.NeedType.PRACTISE_RETAIN,
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("dashboard")

    user.refresh_from_db()
    assert user.primary_need_type == User.NeedType.INTERVIEW_SKILLS
    assert user.secondary_need_type == User.NeedType.PRACTISE_RETAIN


def test_secondary_aim_must_differ_from_primary(user):
    form = NeedTypePreferencesForm(
        data={
            "primary_need_type": User.NeedType.LEARN_ORGANISE,
            "secondary_need_type": User.NeedType.LEARN_ORGANISE,
        },
        instance=user,
    )

    assert form.is_valid() is False
    assert "secondary_need_type" in form.errors


def test_primary_aim_adds_explainable_planner_bonus():
    points, explanation = need_alignment_for_kind(
        primary=User.NeedType.INTERVIEW_SKILLS,
        secondary="",
        kind="PRACTICE",
    )

    assert points == 20
    assert "Build interview skills" in explanation


def test_secondary_aim_uses_reduced_bonus():
    points, explanation = need_alignment_for_kind(
        primary=User.NeedType.LEARN_ORGANISE,
        secondary=User.NeedType.PRACTISE_RETAIN,
        kind="LIBRARY",
    )

    assert points == 30
    assert "both" in explanation
