import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.questions.models import BehaviouralQuestion, DebugQuestion, Question, TechnicalQuestion

pytestmark = pytest.mark.django_db


def test_incomplete_technical_question_cannot_be_marked_ready(user):
    question = TechnicalQuestion.objects.create(
        owner=user,
        title="Two Sum",
        prompt="Solve Two Sum",
    )

    with pytest.raises(ValidationError):
        question.mark_ready()

    question.refresh_from_db()
    assert question.status == Question.Status.NEEDS_NOTES
    assert question.readiness_errors() == ["intuition or solution notes"]


def test_technical_question_can_be_marked_ready_with_solution_notes(user):
    question = TechnicalQuestion.objects.create(
        owner=user,
        title="Two Sum",
        prompt="Solve Two Sum",
        intuition="Look for the complement in a hash map.",
    )

    question.mark_ready()

    question.refresh_from_db()
    assert question.status == Question.Status.READY_FOR_REVIEW


def test_behavioural_question_requires_star_answer(user):
    question = BehaviouralQuestion.objects.create(
        owner=user,
        title="Conflict",
        prompt="Tell me about a conflict.",
    )

    assert question.readiness_errors() == ["STAR answer"]


def test_debug_question_requires_diagnosis_or_fix(user):
    question = DebugQuestion.objects.create(
        owner=user,
        title="Null bug",
        prompt="Why does this fail for null?",
    )

    assert question.readiness_errors() == ["diagnosis or fix"]


def test_bulk_mark_ready_processes_each_question_independently(client, user):
    ready = TechnicalQuestion.objects.create(
        owner=user,
        title="Ready",
        prompt="Explain Two Sum",
        optimal_approach="Use a hash map.",
    )
    incomplete = BehaviouralQuestion.objects.create(
        owner=user,
        title="Incomplete",
        prompt="Tell me about a conflict.",
    )
    client.force_login(user)

    response = client.post(
        reverse("questions:bulk_mark_ready"),
        {"selected_questions": [ready.pk, incomplete.pk]},
        follow=True,
    )

    ready.refresh_from_db()
    incomplete.refresh_from_db()
    assert response.status_code == 200
    assert ready.status == Question.Status.READY_FOR_REVIEW
    assert incomplete.status == Question.Status.NEEDS_NOTES
    content = response.content.decode()
    assert "1 question marked ready" in content
    assert "Incomplete: missing STAR answer" in content


def test_mark_ready_endpoint_rejects_another_users_question(
    client,
    other_user,
    technical_question,
):
    client.force_login(other_user)

    response = client.post(reverse("questions:mark_ready", args=[technical_question.pk]))

    assert response.status_code == 404
