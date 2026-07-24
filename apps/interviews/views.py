from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import MockInterviewCreateForm, MockInterviewResponseForm
from .models import MockInterview, MockInterviewItem
from .services import (
    NoInterviewQuestionsError,
    abandon_mock_interview,
    create_mock_interview,
    mock_interview_summary,
    record_mock_interview_response,
    start_mock_interview,
)


def _owned_interviews(user):
    return MockInterview.objects.filter(user=user)


def _owned_interview(user, interview_id):
    return get_object_or_404(
        _owned_interviews(user).prefetch_related("items"),
        pk=interview_id,
    )


@login_required
def interview_list(request):
    interviews = _owned_interviews(request.user)
    active_interviews = interviews.filter(
        status__in=[
            MockInterview.Status.READY,
            MockInterview.Status.IN_PROGRESS,
        ]
    )[:4]
    completed_interviews = interviews.filter(
        status__in=[
            MockInterview.Status.COMPLETED,
            MockInterview.Status.ABANDONED,
        ]
    )[:8]

    return render(
        request,
        "interviews/interview_list.html",
        {
            "active_interviews": active_interviews,
            "completed_interviews": completed_interviews,
            "completed_count": interviews.filter(
                status=MockInterview.Status.COMPLETED
            ).count(),
        },
    )


@login_required
def interview_create(request):
    if request.method == "POST":
        form = MockInterviewCreateForm(request.POST)
        if form.is_valid():
            try:
                interview = create_mock_interview(
                    user=request.user,
                    focus=form.cleaned_data["focus"],
                    duration_minutes=form.cleaned_data["duration_minutes"],
                )
            except NoInterviewQuestionsError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(
                    request,
                    (
                        f"Mock interview ready with {interview.question_count} "
                        f"question{'s' if interview.question_count != 1 else ''}."
                    ),
                )
                return redirect("interviews:session", interview_id=interview.pk)
    else:
        form = MockInterviewCreateForm()

    return render(
        request,
        "interviews/interview_create.html",
        {"form": form},
    )


@login_required
def interview_session(request, interview_id):
    interview = _owned_interview(request.user, interview_id)

    if interview.is_finished:
        return redirect("interviews:summary", interview_id=interview.pk)

    start_mock_interview(interview=interview)
    current_item = interview.current_item
    if current_item is None:
        interview.status = MockInterview.Status.COMPLETED
        interview.completed_at = interview.completed_at or timezone.now()
        interview.save(
            update_fields=[
                "status",
                "completed_at",
                "updated_at",
            ]
        )
        return redirect("interviews:summary", interview_id=interview.pk)

    form = MockInterviewResponseForm(
        initial={"response_notes": current_item.response_notes}
    )

    return render(
        request,
        "interviews/interview_session.html",
        {
            "interview": interview,
            "item": current_item,
            "form": form,
            "answered_count": interview.answered_count,
        },
    )


@login_required
@require_POST
def interview_submit(request, interview_id, item_id):
    item = get_object_or_404(
        MockInterviewItem.objects.select_related("interview"),
        pk=item_id,
        interview_id=interview_id,
        interview__user=request.user,
    )
    form = MockInterviewResponseForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Choose an assessment before continuing.")
        return redirect("interviews:session", interview_id=interview_id)

    try:
        interview = record_mock_interview_response(
            item=item,
            assessment=form.cleaned_data["assessment"],
            response_notes=form.cleaned_data["response_notes"],
        )
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
        return redirect("interviews:session", interview_id=interview_id)

    if interview.status == MockInterview.Status.COMPLETED:
        messages.success(request, "Mock interview complete. Review the debrief.")
        return redirect("interviews:summary", interview_id=interview.pk)

    return redirect("interviews:session", interview_id=interview.pk)


@login_required
def interview_summary(request, interview_id):
    interview = _owned_interview(request.user, interview_id)
    return render(
        request,
        "interviews/interview_summary.html",
        mock_interview_summary(interview=interview),
    )


@login_required
@require_POST
def interview_abandon(request, interview_id):
    interview = get_object_or_404(
        _owned_interviews(request.user),
        pk=interview_id,
    )
    abandon_mock_interview(interview=interview)
    messages.info(request, "Mock interview ended early. Your completed answers were saved.")
    return redirect("interviews:summary", interview_id=interview.pk)
