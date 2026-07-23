import pytest
from django.urls import reverse
from django.utils import timezone

from apps.questions.models import Question, TechnicalQuestion
from apps.reviews.models import ReviewAttempt, ReviewState

pytestmark = pytest.mark.django_db


def _ready_question(user, title="Two Sum"):
    return TechnicalQuestion.objects.create(
        owner=user,
        title=title,
        prompt="Return two indices whose values sum to the target.",
        status=Question.Status.READY_FOR_REVIEW,
        intuition="Look up the complement before inserting.",
        optimal_approach="Use a hash map.",
    )


def test_queue_lists_due_ready_questions(client, user):
    question = _ready_question(user)
    client.force_login(user)

    response = client.get(reverse("reviews:queue"))

    assert response.status_code == 200
    assert question.title in response.content.decode()
    assert response.context["summary"]["due_count"] == 1


def test_user_cannot_review_another_users_question(client, user, other_user):
    question = _ready_question(other_user)
    client.force_login(user)

    response = client.get(
        reverse("reviews:review", args=[question.pk])
    )

    assert response.status_code == 404


def test_submitting_rating_records_attempt_and_reschedules(client, user):
    question = _ready_question(user)
    state = ReviewState.objects.create(
        user=user,
        question=question,
        due_at=timezone.now(),
    )
    client.force_login(user)

    response = client.post(
        reverse("reviews:submit", args=[question.pk]),
        {"rating": ReviewAttempt.Rating.GOOD},
    )

    assert response.status_code == 302
    state.refresh_from_db()
    assert state.interval_days == 1
    assert state.attempts.count() == 1


def test_dashboard_shows_due_review_count(client, user):
    _ready_question(user)
    client.force_login(user)

    response = client.get(reverse("dashboard"))

    assert response.status_code == 200
    assert response.context["due_review_count"] == 1
