from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.questions.models import Question, TechnicalQuestion
from apps.reviews.models import ReviewAttempt, ReviewState
from apps.reviews.services import (
    due_review_states,
    record_review,
    sync_ready_review_states,
)

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


def test_sync_creates_states_only_for_ready_owned_questions(user):
    ready = _ready_question(user)
    TechnicalQuestion.objects.create(
        owner=user,
        title="Draft",
        prompt="Not ready.",
        status=Question.Status.NEEDS_NOTES,
    )

    sync_ready_review_states(user=user)

    states = ReviewState.objects.filter(user=user)
    assert states.count() == 1
    assert states.get().question_id == ready.pk


def test_good_rating_uses_one_three_then_ease_intervals(user):
    question = _ready_question(user)
    now = timezone.now()
    state = ReviewState.objects.create(
        user=user,
        question=question,
        due_at=now,
    )

    record_review(
        state=state,
        rating=ReviewAttempt.Rating.GOOD,
        now=now,
    )
    state.refresh_from_db()
    assert state.interval_days == 1

    second_time = now + timedelta(days=1)
    record_review(
        state=state,
        rating=ReviewAttempt.Rating.GOOD,
        now=second_time,
    )
    state.refresh_from_db()
    assert state.interval_days == 3

    third_time = second_time + timedelta(days=3)
    record_review(
        state=state,
        rating=ReviewAttempt.Rating.GOOD,
        now=third_time,
    )
    state.refresh_from_db()
    assert state.interval_days == 8
    assert state.repetitions == 3


def test_again_rating_records_lapse_and_short_retry(user):
    question = _ready_question(user)
    now = timezone.now()
    state = ReviewState.objects.create(
        user=user,
        question=question,
        due_at=now,
        interval_days=8,
        repetitions=3,
        ease_factor=Decimal("2.50"),
    )

    attempt = record_review(
        state=state,
        rating=ReviewAttempt.Rating.AGAIN,
        now=now,
    )
    state.refresh_from_db()

    assert state.interval_days == 0
    assert state.repetitions == 0
    assert state.lapses == 1
    assert state.due_at == now + timedelta(minutes=10)
    assert state.ease_factor == Decimal("2.30")
    assert attempt.previous_interval_days == 8


def test_due_queue_orders_oldest_due_first(user):
    first_question = _ready_question(user, "First")
    second_question = _ready_question(user, "Second")
    now = timezone.now()

    ReviewState.objects.create(
        user=user,
        question=second_question,
        due_at=now - timedelta(minutes=5),
    )
    ReviewState.objects.create(
        user=user,
        question=first_question,
        due_at=now - timedelta(hours=1),
    )

    states = list(due_review_states(user=user, now=now))

    assert [state.question_id for state in states] == [
        first_question.pk,
        second_question.pk,
    ]
