from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from apps.questions.models import Question

from .models import ReviewAttempt, ReviewState

MINIMUM_EASE = Decimal("1.30")
AGAIN_DELAY_MINUTES = 10


def sync_ready_review_states(*, user, now=None):
    current_time = now or timezone.now()
    ready_question_ids = Question.objects.filter(
        owner=user,
        status=Question.Status.READY_FOR_REVIEW,
    ).values_list("pk", flat=True)

    existing_ids = set(
        ReviewState.objects.filter(
            user=user,
            question_id__in=ready_question_ids,
        ).values_list("question_id", flat=True)
    )

    ReviewState.objects.bulk_create(
        [
            ReviewState(
                user=user,
                question_id=question_id,
                due_at=current_time,
            )
            for question_id in ready_question_ids
            if question_id not in existing_ids
        ],
        ignore_conflicts=True,
    )


def due_review_states(*, user, now=None):
    current_time = now or timezone.now()
    sync_ready_review_states(user=user, now=current_time)
    return (
        ReviewState.objects.filter(
            user=user,
            question__owner=user,
            question__status=Question.Status.READY_FOR_REVIEW,
            due_at__lte=current_time,
        )
        .select_related(
            "question",
            "question__technicalquestion",
            "question__conceptquestion",
            "question__behaviouralquestion",
            "question__debugquestion",
        )
        .order_by("due_at", "pk")
    )


def upcoming_review_states(*, user, now=None):
    current_time = now or timezone.now()
    sync_ready_review_states(user=user, now=current_time)
    return (
        ReviewState.objects.filter(
            user=user,
            question__owner=user,
            question__status=Question.Status.READY_FOR_REVIEW,
            due_at__gt=current_time,
        )
        .select_related("question")
        .order_by("due_at", "pk")
    )


def review_dashboard_summary(*, user, now=None):
    current_time = now or timezone.now()
    sync_ready_review_states(user=user, now=current_time)

    active_states = ReviewState.objects.filter(
        user=user,
        question__owner=user,
        question__status=Question.Status.READY_FOR_REVIEW,
    )
    due_states = active_states.filter(due_at__lte=current_time)
    next_state = active_states.order_by("due_at", "pk").first()

    return {
        "due_count": due_states.count(),
        "scheduled_count": active_states.count(),
        "reviewed_today_count": ReviewAttempt.objects.filter(
            state__user=user,
            reviewed_at__date=timezone.localdate(current_time),
        ).count(),
        "next_state": next_state,
    }


def _rounded_days(value):
    rounded = value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return max(1, int(rounded))


def _schedule_values(*, state, rating, now):
    previous_interval = state.interval_days
    previous_ease = state.ease_factor

    if rating == ReviewAttempt.Rating.AGAIN:
        interval_days = 0
        due_at = now + timedelta(minutes=AGAIN_DELAY_MINUTES)
        repetitions = 0
        lapses = state.lapses + 1
        ease_factor = max(MINIMUM_EASE, previous_ease - Decimal("0.20"))
    elif rating == ReviewAttempt.Rating.HARD:
        if state.repetitions == 0:
            interval_days = 1
        else:
            base_interval = Decimal(max(previous_interval, 1))
            interval_days = _rounded_days(base_interval * Decimal("1.20"))
        due_at = now + timedelta(days=interval_days)
        repetitions = state.repetitions + 1
        lapses = state.lapses
        ease_factor = max(MINIMUM_EASE, previous_ease - Decimal("0.15"))
    elif rating == ReviewAttempt.Rating.GOOD:
        if state.repetitions == 0:
            interval_days = 1
        elif state.repetitions == 1:
            interval_days = 3
        else:
            base_interval = Decimal(max(previous_interval, 1))
            interval_days = _rounded_days(base_interval * previous_ease)
        due_at = now + timedelta(days=interval_days)
        repetitions = state.repetitions + 1
        lapses = state.lapses
        ease_factor = previous_ease
    elif rating == ReviewAttempt.Rating.EASY:
        if state.repetitions == 0:
            interval_days = 4
        else:
            base_interval = Decimal(max(previous_interval, 1))
            interval_days = max(
                4,
                _rounded_days(
                    base_interval * previous_ease * Decimal("1.30")
                ),
            )
        due_at = now + timedelta(days=interval_days)
        repetitions = state.repetitions + 1
        lapses = state.lapses
        ease_factor = previous_ease + Decimal("0.15")
    else:
        raise ValueError("Unsupported review rating.")

    return {
        "due_at": due_at,
        "interval_days": interval_days,
        "repetitions": repetitions,
        "lapses": lapses,
        "ease_factor": ease_factor,
    }


def rating_previews(*, state, now=None):
    current_time = now or timezone.now()
    previews = []

    for value, label in ReviewAttempt.Rating.choices:
        scheduled = _schedule_values(
            state=state,
            rating=value,
            now=current_time,
        )
        if value == ReviewAttempt.Rating.AGAIN:
            interval_label = f"{AGAIN_DELAY_MINUTES} min"
        elif scheduled["interval_days"] == 1:
            interval_label = "1 day"
        else:
            interval_label = f"{scheduled['interval_days']} days"

        previews.append(
            {
                "value": value,
                "label": label,
                "interval_label": interval_label,
            }
        )

    return previews


def record_review(*, state, rating, now=None):
    current_time = now or timezone.now()

    with transaction.atomic():
        locked_state = (
            ReviewState.objects.select_for_update()
            .select_related("question")
            .get(pk=state.pk)
        )
        if locked_state.question.owner_id != locked_state.user_id:
            raise ValueError("Review state ownership is invalid.")
        if locked_state.question.status != Question.Status.READY_FOR_REVIEW:
            raise ValueError("Only ready questions can be reviewed.")

        scheduled = _schedule_values(
            state=locked_state,
            rating=rating,
            now=current_time,
        )

        attempt = ReviewAttempt.objects.create(
            state=locked_state,
            rating=rating,
            reviewed_at=current_time,
            previous_due_at=locked_state.due_at,
            scheduled_due_at=scheduled["due_at"],
            previous_interval_days=locked_state.interval_days,
            scheduled_interval_days=scheduled["interval_days"],
            previous_ease_factor=locked_state.ease_factor,
            scheduled_ease_factor=scheduled["ease_factor"],
        )

        locked_state.due_at = scheduled["due_at"]
        locked_state.interval_days = scheduled["interval_days"]
        locked_state.ease_factor = scheduled["ease_factor"]
        locked_state.repetitions = scheduled["repetitions"]
        locked_state.lapses = scheduled["lapses"]
        locked_state.last_reviewed_at = current_time
        locked_state.save(
            update_fields=[
                "due_at",
                "interval_days",
                "ease_factor",
                "repetitions",
                "lapses",
                "last_reviewed_at",
                "updated_at",
            ]
        )

    return attempt
