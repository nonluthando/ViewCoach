from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.questions.models import Question

from .models import ReviewAttempt, ReviewState
from .services import (
    due_review_states,
    rating_previews,
    record_review,
    review_dashboard_summary,
    upcoming_review_states,
)


def _ready_question_for_user(user, pk):
    return get_object_or_404(
        Question.objects.select_related(
            "technicalquestion",
            "conceptquestion",
            "behaviouralquestion",
            "debugquestion",
        ),
        pk=pk,
        owner=user,
        status=Question.Status.READY_FOR_REVIEW,
    )


@login_required
def review_queue(request):
    current_time = timezone.now()
    summary = review_dashboard_summary(
        user=request.user,
        now=current_time,
    )
    due_states = list(
        due_review_states(
            user=request.user,
            now=current_time,
        )[:20]
    )
    upcoming_states = list(
        upcoming_review_states(
            user=request.user,
            now=current_time,
        )[:8]
    )

    return render(
        request,
        "reviews/review_queue.html",
        {
            "summary": summary,
            "due_states": due_states,
            "upcoming_states": upcoming_states,
        },
    )


@login_required
def review_question(request, pk):
    question = _ready_question_for_user(request.user, pk)
    state, _ = ReviewState.objects.get_or_create(
        user=request.user,
        question=question,
        defaults={"due_at": timezone.now()},
    )

    return render(
        request,
        "reviews/review_question.html",
        {
            "question": question,
            "specific": question.specific,
            "review_state": state,
            "rating_previews": rating_previews(state=state),
        },
    )


@login_required
@require_POST
def submit_review(request, pk):
    question = _ready_question_for_user(request.user, pk)
    state, _ = ReviewState.objects.get_or_create(
        user=request.user,
        question=question,
        defaults={"due_at": timezone.now()},
    )
    rating = request.POST.get("rating", "")
    valid_ratings = {value for value, _ in ReviewAttempt.Rating.choices}
    if rating not in valid_ratings:
        messages.error(request, "Choose how well you recalled the answer.")
        return redirect("reviews:review", pk=question.pk)

    attempt = record_review(
        state=state,
        rating=rating,
    )
    messages.success(
        request,
        (
            f"Review recorded as {attempt.get_rating_display()}. "
            f"Next review: {attempt.scheduled_due_at:%d %b %Y}."
        ),
    )

    next_state = due_review_states(user=request.user).first()
    if next_state is not None:
        return redirect(
            "reviews:review",
            pk=next_state.question_id,
        )
    return redirect("reviews:queue")


@login_required
def review_history(request):
    attempts = (
        ReviewAttempt.objects.filter(
            state__user=request.user,
            state__question__owner=request.user,
        )
        .select_related("state", "state__question")
        .order_by("-reviewed_at", "-pk")
    )
    page = Paginator(attempts, 25).get_page(request.GET.get("page"))

    return render(
        request,
        "reviews/review_history.html",
        {"page": page},
    )
