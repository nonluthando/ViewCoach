import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.evidence.ai_prep import AI_ASSISTED_INTERVIEW_QUESTIONS
from apps.evidence.models import AIPrepAnswer, EvidenceItem

pytestmark = pytest.mark.django_db


def test_ai_coding_prep_contains_heavy_question_and_follow_up_coverage():
    follow_up_count = sum(
        len(question.follow_ups) for question in AI_ASSISTED_INTERVIEW_QUESTIONS
    )

    assert len(AI_ASSISTED_INTERVIEW_QUESTIONS) >= 15
    assert follow_up_count >= 100


def test_ai_coding_prep_requires_authentication(client):
    response = client.get(reverse("evidence:ai_coding_prep"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


def test_ai_coding_prep_displays_questions_and_follow_ups(client, user):
    client.force_login(user)

    response = client.get(reverse("evidence:ai_coding_prep"))
    html = response.content.decode()

    assert response.status_code == 200
    assert "How do you use AI while coding?" in html
    assert "What do you do yourself before asking AI for help?" in html
    assert "How would you use AI in a timed repository assessment?" in html


def test_user_can_save_ai_prep_answer_with_owned_evidence(
    client,
    user,
    evidence_item,
):
    client.force_login(user)

    response = client.post(
        reverse("evidence:ai_prep_answer_save", args=["verify-ai-code"]),
        {
            "answer_notes": "I run targeted tests, then the complete suite.",
            "supporting_evidence": evidence_item.pk,
        },
    )

    answer = AIPrepAnswer.objects.get(
        user=user,
        question_key="verify-ai-code",
    )
    assert response.status_code == 302
    assert response.url == reverse("evidence:ai_coding_prep")
    assert answer.supporting_evidence == evidence_item


def test_user_cannot_link_another_users_evidence_to_ai_answer(
    client,
    user,
    other_evidence,
):
    client.force_login(user)

    response = client.post(
        reverse("evidence:ai_prep_answer_save", args=["verify-ai-code"]),
        {
            "answer_notes": "Private evidence must not be accepted.",
            "supporting_evidence": other_evidence.pk,
        },
    )

    assert response.status_code == 302
    assert not AIPrepAnswer.objects.filter(user=user).exists()


def test_unknown_ai_question_returns_404(client, user):
    client.force_login(user)

    response = client.post(
        reverse("evidence:ai_prep_answer_save", args=["not-a-real-question"]),
        {"answer_notes": "No answer."},
    )

    assert response.status_code == 404


def test_ai_prep_page_does_not_show_another_users_answer(
    client,
    user,
    other_user,
):
    AIPrepAnswer.objects.create(
        user=other_user,
        question_key="ai-coding-workflow",
        answer_notes="This answer is private.",
    )
    client.force_login(user)

    response = client.get(reverse("evidence:ai_coding_prep"))

    assert "This answer is private." not in response.content.decode()


def test_ai_prep_answer_rejects_unknown_question_key(user):
    answer = AIPrepAnswer(
        user=user,
        question_key="unknown-question",
        answer_notes="Invalid.",
    )

    with pytest.raises(ValidationError):
        answer.full_clean()


def test_ai_prep_answer_rejects_supporting_evidence_from_another_user(
    user,
    other_evidence,
):
    answer = AIPrepAnswer(
        user=user,
        question_key="ai-coding-workflow",
        answer_notes="Invalid evidence link.",
        supporting_evidence=other_evidence,
    )

    with pytest.raises(ValidationError):
        answer.full_clean()


def test_ai_prep_answer_is_unique_per_user_and_question(user):
    AIPrepAnswer.objects.create(
        user=user,
        question_key="ai-coding-workflow",
    )
    duplicate = AIPrepAnswer(
        user=user,
        question_key="ai-coding-workflow",
    )

    with pytest.raises(ValidationError):
        duplicate.full_clean()


def test_ai_prep_answer_can_link_work_or_incident_evidence(user):
    incident = EvidenceItem.objects.create(
        owner=user,
        source_type=EvidenceItem.SourceType.INCIDENT,
        title="Failed integration patch",
    )
    answer = AIPrepAnswer(
        user=user,
        question_key="debug-failing-tests-with-ai",
        supporting_evidence=incident,
    )

    answer.full_clean()

