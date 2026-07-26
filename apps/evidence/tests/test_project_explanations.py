import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.evidence.models import EvidenceItem, ProjectExplanation

pytestmark = pytest.mark.django_db


def explanation_payload():
    return {
        "quick_pitch": "ViewCoach tells candidates what to study next.",
        "two_minute_answer": "I built ViewCoach as a Django interview preparation platform.",
        "architecture": "Django applications share a PostgreSQL database.",
        "key_decisions": "Keep planning deterministic and explainable.",
        "difficult_bug": "A dashboard test could not discover a sibling fixture.",
        "testing_and_verification": "Ran pytest, Ruff and the migration check.",
        "ai_use": (
            "Used AI coding tools to investigate failures, implement fixes and verify "
            "solutions through tests and code review."
        ),
        "tradeoffs": "Deterministic rules require explicit maintenance.",
        "improvements": "Add richer curriculum mappings.",
        "scaling": "Move expensive generation work to background jobs.",
        "likely_follow_ups": "Why Django?\nWhy PostgreSQL?",
    }


def test_project_explanations_require_authentication(client):
    response = client.get(reverse("evidence:project_explanations"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


def test_user_can_save_a_project_explanation(client, user, evidence_item):
    client.force_login(user)

    response = client.post(
        reverse("evidence:project_explanation_edit", args=[evidence_item.pk]),
        explanation_payload(),
    )

    explanation = ProjectExplanation.objects.get(evidence=evidence_item)
    assert response.status_code == 302
    assert response.url == reverse("evidence:project_explanations")
    assert explanation.quick_pitch.startswith("ViewCoach")


def test_project_explanations_show_the_users_project_explanation(
    client,
    user,
    evidence_item,
):
    ProjectExplanation.objects.create(
        evidence=evidence_item,
        quick_pitch="A focused project explanation.",
    )
    client.force_login(user)

    response = client.get(reverse("evidence:project_explanations"))

    assert response.status_code == 200
    assert evidence_item.title in response.content.decode()
    assert "A focused project explanation." in response.content.decode()


def test_project_explanations_do_not_show_other_users_projects(
    client,
    user,
    other_user,
):
    private_project = EvidenceItem.objects.create(
        owner=other_user,
        source_type=EvidenceItem.SourceType.PROJECT,
        title="Private project",
    )
    ProjectExplanation.objects.create(
        evidence=private_project,
        quick_pitch="This must remain private.",
    )
    client.force_login(user)

    response = client.get(reverse("evidence:project_explanations"))
    html = response.content.decode()

    assert "Private project" not in html
    assert "This must remain private." not in html


def test_user_cannot_edit_another_users_project_explanation(
    client,
    user,
    other_user,
):
    private_project = EvidenceItem.objects.create(
        owner=other_user,
        source_type=EvidenceItem.SourceType.PROJECT,
        title="Private project",
    )
    client.force_login(user)

    response = client.get(
        reverse("evidence:project_explanation_edit", args=[private_project.pk])
    )

    assert response.status_code == 404


def test_project_explanation_rejects_non_project_evidence(user):
    work_item = EvidenceItem.objects.create(
        owner=user,
        source_type=EvidenceItem.SourceType.WORK,
        title="Work example",
    )
    explanation = ProjectExplanation(
        evidence=work_item,
        quick_pitch="This should not validate.",
    )

    with pytest.raises(ValidationError):
        explanation.full_clean()


def test_non_project_evidence_cannot_open_the_explanation_form(client, user):
    work_item = EvidenceItem.objects.create(
        owner=user,
        source_type=EvidenceItem.SourceType.WORK,
        title="Work example",
    )
    client.force_login(user)

    response = client.get(
        reverse("evidence:project_explanation_edit", args=[work_item.pk])
    )

    assert response.status_code == 404
