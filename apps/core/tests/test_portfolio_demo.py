from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.evidence.models import (
    BehaviouralStory,
    DecisionRecord,
    EvidenceItem,
    ProjectExplanation,
)
from apps.goals.models import InterviewGoal
from apps.interviews.models import MockInterview
from apps.questions.models import Question
from apps.reviews.models import ReviewAttempt, ReviewState
from apps.roadmaps.models import (
    Roadmap,
    UserRoadmap,
    YouTubePlaylistRoadmap,
)

pytestmark = pytest.mark.django_db


def _start_demo(client):
    return client.post(reverse("portfolio_demo_start"))


def test_project_showcase_is_public(client):
    response = client.get(reverse("project_showcase"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "ViewCoach turns scattered interview preparation" in content
    assert "Engineering decisions" in content


@override_settings(PORTFOLIO_DEMO_ENABLED=False)
def test_demo_start_returns_404_when_disabled(client):
    response = _start_demo(client)

    assert response.status_code == 404
    assert not User.objects.filter(
        email__endswith="@demo.viewcoach.local"
    ).exists()


@override_settings(
    PORTFOLIO_DEMO_ENABLED=True,
    PORTFOLIO_DEMO_SESSION_SECONDS=7200,
    PORTFOLIO_DEMO_MAX_ACTIVE=25,
)
def test_demo_start_creates_complete_isolated_workspace(client):
    response = _start_demo(client)

    assert response.status_code == 302
    assert response.url == reverse("portfolio_demo_guide")

    demo_user = User.objects.get(email__endswith="@demo.viewcoach.local")
    assert client.session["_auth_user_id"] == str(demo_user.pk)
    assert client.session["portfolio_demo"] is True

    assert Roadmap.objects.filter(created_by=demo_user).count() == 2
    assert Roadmap.objects.filter(
        created_by=demo_user,
        source=Roadmap.Source.CUSTOM,
    ).exists()
    assert YouTubePlaylistRoadmap.objects.filter(
        user=demo_user,
        is_favourite=True,
    ).exists()
    assert UserRoadmap.objects.filter(
        user=demo_user,
        is_focused=True,
    ).exists()

    assert Question.objects.filter(owner=demo_user).count() == 4
    assert ReviewState.objects.filter(user=demo_user).count() == 4
    assert ReviewAttempt.objects.filter(state__user=demo_user).exists()
    assert EvidenceItem.objects.filter(owner=demo_user).count() == 3
    assert ProjectExplanation.objects.filter(
        evidence__owner=demo_user
    ).count() == 2
    assert DecisionRecord.objects.filter(evidence__owner=demo_user).exists()
    assert BehaviouralStory.objects.filter(evidence__owner=demo_user).exists()
    assert InterviewGoal.objects.filter(
        user=demo_user,
        is_primary=True,
    ).exists()
    assert MockInterview.objects.filter(
        user=demo_user,
        status=MockInterview.Status.COMPLETED,
    ).exists()


@override_settings(
    PORTFOLIO_DEMO_ENABLED=True,
    PORTFOLIO_DEMO_SESSION_SECONDS=7200,
    PORTFOLIO_DEMO_MAX_ACTIVE=25,
)
def test_each_browser_receives_a_different_demo_account():
    first_client = Client()
    second_client = Client()

    _start_demo(first_client)
    _start_demo(second_client)

    assert first_client.session["_auth_user_id"] != second_client.session[
        "_auth_user_id"
    ]


@override_settings(
    PORTFOLIO_DEMO_ENABLED=True,
    PORTFOLIO_DEMO_SESSION_SECONDS=7200,
    PORTFOLIO_DEMO_MAX_ACTIVE=25,
)
def test_tour_step_records_progress_and_redirects(client):
    _start_demo(client)

    response = client.get(
        reverse(
            "portfolio_demo_step",
            kwargs={"step_key": "dashboard"},
        )
    )

    assert response.status_code == 302
    assert response.url == reverse("dashboard")
    assert "dashboard" in client.session["portfolio_demo_completed_steps"]


@override_settings(
    PORTFOLIO_DEMO_ENABLED=True,
    PORTFOLIO_DEMO_SESSION_SECONDS=7200,
    PORTFOLIO_DEMO_MAX_ACTIVE=25,
)
def test_demo_reset_replaces_user_and_restores_seeded_data(client):
    _start_demo(client)
    old_user_id = int(client.session["_auth_user_id"])
    Question.objects.filter(owner_id=old_user_id).delete()

    response = client.post(reverse("portfolio_demo_reset"))

    new_user_id = int(client.session["_auth_user_id"])
    assert response.status_code == 302
    assert new_user_id != old_user_id
    assert not User.objects.filter(pk=old_user_id).exists()
    assert Question.objects.filter(owner_id=new_user_id).count() == 4


@override_settings(
    PORTFOLIO_DEMO_ENABLED=True,
    PORTFOLIO_DEMO_SESSION_SECONDS=7200,
    PORTFOLIO_DEMO_MAX_ACTIVE=25,
)
def test_demo_end_logs_out_and_deletes_user(client):
    _start_demo(client)
    user_id = int(client.session["_auth_user_id"])

    response = client.post(reverse("portfolio_demo_end"))

    assert response.status_code == 302
    assert response.url == reverse("project_showcase")
    assert not User.objects.filter(pk=user_id).exists()
    assert "_auth_user_id" not in client.session


@override_settings(
    PORTFOLIO_DEMO_ENABLED=True,
    PORTFOLIO_DEMO_SESSION_SECONDS=7200,
    PORTFOLIO_DEMO_MAX_ACTIVE=0,
)
def test_capacity_limit_returns_friendly_503(client):
    response = _start_demo(client)

    assert response.status_code == 503
    assert "currently in use" in response.content.decode()


@override_settings(
    PORTFOLIO_DEMO_ENABLED=True,
    PORTFOLIO_DEMO_SESSION_SECONDS=7200,
    PORTFOLIO_DEMO_MAX_ACTIVE=25,
)
def test_demo_middleware_blocks_live_ai_generation(client):
    _start_demo(client)
    assets = client.session["portfolio_demo_assets"]

    response = client.post(
        reverse(
            "roadmaps:generate_topic_questions",
            kwargs={
                "slug": assets["custom_roadmap_slug"],
                "topic_id": assets["featured_topic_id"],
            },
        ),
        {"count": 3},
    )

    assert response.status_code == 302
    assert response.url == reverse("portfolio_demo_guide")


@override_settings(
    PORTFOLIO_DEMO_ENABLED=True,
    PORTFOLIO_DEMO_SESSION_SECONDS=7200,
    PORTFOLIO_DEMO_MAX_ACTIVE=25,
    PORTFOLIO_DEMO_TTL_HOURS=24,
)
def test_cleanup_command_deletes_expired_demo_users(client):
    _start_demo(client)
    user_id = int(client.session["_auth_user_id"])
    User.objects.filter(pk=user_id).update(
        date_joined=timezone.now() - timedelta(hours=25)
    )
    output = StringIO()

    call_command("cleanup_portfolio_demo_users", stdout=output)

    assert not User.objects.filter(pk=user_id).exists()
    assert "Deleted 1 temporary portfolio demo user." in output.getvalue()
