import pytest
from django.urls import reverse

from apps.interviews.models import MockInterview, MockInterviewItem
from apps.interviews.services import create_mock_interview
from apps.questions.models import Question, TechnicalQuestion

pytestmark = pytest.mark.django_db


def test_interview_list_requires_authentication(client):
    response = client.get(reverse("interviews:list"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


def test_user_can_create_a_mock_interview(client, user, technical_question):
    client.force_login(user)

    response = client.post(
        reverse("interviews:create"),
        {
            "focus": MockInterview.Focus.TECHNICAL,
            "duration_minutes": "20",
        },
    )

    interview = MockInterview.objects.get(user=user)
    assert response.status_code == 302
    assert response.url == reverse("interviews:session", args=[interview.pk])
    assert interview.question_count == 1


def test_create_page_shows_question_error_when_library_is_empty(client, user):
    client.force_login(user)

    response = client.post(
        reverse("interviews:create"),
        {
            "focus": MockInterview.Focus.DEBUG,
            "duration_minutes": "20",
        },
    )

    assert response.status_code == 200
    assert "Add or save at least one suitable question" in response.content.decode()
    assert MockInterview.objects.filter(user=user).count() == 0


def test_opening_session_starts_interview(client, user, technical_question):
    interview = create_mock_interview(
        user=user,
        focus=MockInterview.Focus.TECHNICAL,
        duration_minutes=20,
    )
    client.force_login(user)

    response = client.get(reverse("interviews:session", args=[interview.pk]))

    interview.refresh_from_db()
    assert response.status_code == 200
    assert interview.status == MockInterview.Status.IN_PROGRESS
    assert "Question 1 of 1" in response.content.decode()


def test_user_cannot_open_another_users_interview(
    client,
    user,
    other_user,
):
    question = TechnicalQuestion.objects.create(
        owner=other_user,
        title="Other user's question",
        prompt="Explain something private.",
        status=Question.Status.READY_FOR_REVIEW,
        topic="Privacy",
        intuition="Private notes.",
    )
    interview = create_mock_interview(
        user=other_user,
        focus=MockInterview.Focus.TECHNICAL,
        duration_minutes=20,
    )
    assert interview.items.get().question_id == question.pk
    client.force_login(user)

    response = client.get(reverse("interviews:session", args=[interview.pk]))

    assert response.status_code == 404


def test_valid_response_completes_single_question_session(
    client,
    user,
    technical_question,
):
    interview = create_mock_interview(
        user=user,
        focus=MockInterview.Focus.TECHNICAL,
        duration_minutes=20,
    )
    item = interview.items.get()
    client.force_login(user)

    response = client.post(
        reverse("interviews:submit", args=[interview.pk, item.pk]),
        {
            "assessment": MockInterviewItem.Assessment.CONFIDENT,
            "response_notes": "I explained the heap invariant.",
        },
    )

    item.refresh_from_db()
    interview.refresh_from_db()
    assert response.status_code == 302
    assert response.url == reverse("interviews:summary", args=[interview.pk])
    assert item.assessment == MockInterviewItem.Assessment.CONFIDENT
    assert interview.status == MockInterview.Status.COMPLETED


def test_missing_assessment_does_not_advance_session(
    client,
    user,
    technical_question,
):
    interview = create_mock_interview(
        user=user,
        focus=MockInterview.Focus.TECHNICAL,
        duration_minutes=20,
    )
    item = interview.items.get()
    client.force_login(user)

    response = client.post(
        reverse("interviews:submit", args=[interview.pk, item.pk]),
        {"response_notes": "An unfinished answer."},
    )

    item.refresh_from_db()
    assert response.status_code == 302
    assert item.answered_at is None


def test_user_can_end_session_early(client, user, technical_question):
    interview = create_mock_interview(
        user=user,
        focus=MockInterview.Focus.TECHNICAL,
        duration_minutes=20,
    )
    client.force_login(user)

    response = client.post(reverse("interviews:abandon", args=[interview.pk]))

    interview.refresh_from_db()
    assert response.status_code == 302
    assert interview.status == MockInterview.Status.ABANDONED
    assert response.url == reverse("interviews:summary", args=[interview.pk])


def test_interview_history_lists_completed_sessions(
    client,
    user,
    technical_question,
):
    interview = create_mock_interview(
        user=user,
        focus=MockInterview.Focus.TECHNICAL,
        duration_minutes=20,
    )
    item = interview.items.get()
    item.assessment = MockInterviewItem.Assessment.CONFIDENT
    item.answered_at = interview.created_at
    item.save(update_fields=["assessment", "answered_at"])
    interview.status = MockInterview.Status.COMPLETED
    interview.completed_at = interview.created_at
    interview.save(update_fields=["status", "completed_at", "updated_at"])
    client.force_login(user)

    response = client.get(reverse("interviews:list"))

    assert response.status_code == 200
    assert "Recent sessions" in response.content.decode()
    assert reverse("interviews:summary", args=[interview.pk]) in response.content.decode()
