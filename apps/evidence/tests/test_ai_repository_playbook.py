import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.evidence.ai_repository_playbook import (
    PROMPT_TEMPLATES,
    TIMED_REPOSITORY_WORKFLOW,
    VERIFICATION_CHECKLIST,
)
from apps.evidence.models import AIRepositoryPracticeAttempt

pytestmark = pytest.mark.django_db


def attempt_payload():
    return {
        "title": "Storyteller repository practice 1",
        "scenario_type": AIRepositoryPracticeAttempt.ScenarioType.MIXED,
        "practiced_on": "2026-07-26",
        "duration_minutes": 60,
        "tests_fixed": 3,
        "feature_completed": "on",
        "full_suite_passed": "on",
        "ai_use_note": "Used AI to compare two narrow fixes and reviewed the final diff.",
        "reflection": "Read all assertions before changing code.",
    }


def test_playbook_has_complete_workflow_and_prompt_coverage():
    assert len(TIMED_REPOSITORY_WORKFLOW) == 8
    assert len(PROMPT_TEMPLATES) >= 8
    assert len(VERIFICATION_CHECKLIST) >= 10


def test_repository_playbook_requires_authentication(client):
    response = client.get(reverse("evidence:ai_repository_playbook"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


def test_repository_playbook_displays_workflow_prompts_and_verification(client, user):
    client.force_login(user)

    response = client.get(reverse("evidence:ai_repository_playbook"))
    html = response.content.decode()

    assert response.status_code == 200
    assert "Run and classify the failures" in html
    assert "Do not propose code changes yet." in html
    assert "The complete test suite passes." in html
    assert "What I changed or rejected:" in html


def test_user_can_record_repository_practice_attempt(client, user):
    client.force_login(user)

    response = client.post(
        reverse("evidence:ai_repository_attempt_add"),
        attempt_payload(),
    )

    attempt = AIRepositoryPracticeAttempt.objects.get(user=user)
    assert response.status_code == 302
    assert response.url == reverse("evidence:ai_repository_playbook")
    assert attempt.tests_fixed == 3
    assert attempt.feature_completed is True
    assert attempt.full_suite_passed is True


def test_repository_playbook_only_shows_current_users_attempts(
    client,
    user,
    other_user,
):
    AIRepositoryPracticeAttempt.objects.create(
        user=other_user,
        title="Private practice attempt",
    )
    client.force_login(user)

    response = client.get(reverse("evidence:ai_repository_playbook"))

    assert "Private practice attempt" not in response.content.decode()


def test_user_cannot_delete_another_users_attempt(
    client,
    user,
    other_user,
):
    attempt = AIRepositoryPracticeAttempt.objects.create(
        user=other_user,
        title="Private practice attempt",
    )
    client.force_login(user)

    response = client.post(reverse("evidence:ai_repository_attempt_delete", args=[attempt.pk]))

    assert response.status_code == 404
    assert AIRepositoryPracticeAttempt.objects.filter(pk=attempt.pk).exists()


def test_user_can_delete_own_attempt(client, user):
    attempt = AIRepositoryPracticeAttempt.objects.create(
        user=user,
        title="Practice attempt",
    )
    client.force_login(user)

    response = client.post(reverse("evidence:ai_repository_attempt_delete", args=[attempt.pk]))

    assert response.status_code == 302
    assert not AIRepositoryPracticeAttempt.objects.filter(pk=attempt.pk).exists()


@pytest.mark.parametrize("duration", [0, 14, 181, 500])
def test_practice_attempt_rejects_unreasonable_duration(user, duration):
    attempt = AIRepositoryPracticeAttempt(
        user=user,
        title="Practice attempt",
        duration_minutes=duration,
    )

    with pytest.raises(ValidationError):
        attempt.full_clean()


@pytest.mark.parametrize("duration", [15, 60, 180])
def test_practice_attempt_accepts_supported_duration(user, duration):
    attempt = AIRepositoryPracticeAttempt(
        user=user,
        title="Practice attempt",
        duration_minutes=duration,
    )

    attempt.full_clean()


def test_practice_outcome_labels(user):
    completed = AIRepositoryPracticeAttempt(
        user=user,
        title="Completed",
        feature_completed=True,
        full_suite_passed=True,
    )
    partial = AIRepositoryPracticeAttempt(
        user=user,
        title="Partial",
        tests_fixed=1,
    )

    assert completed.outcome_label == "Completed and verified"
    assert partial.outcome_label == "Partially completed"
