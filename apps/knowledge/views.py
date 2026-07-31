from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .answering import AnswerGenerationError, answer_question
from .forms import HelpAssistantForm
from .models import KnowledgeQueryLog


def _rate_limit_exceeded(user):
    window_started_at = timezone.now() - timedelta(
        seconds=settings.RAG_RATE_LIMIT_WINDOW_SECONDS
    )
    request_count = KnowledgeQueryLog.objects.filter(
        user=user,
        created_at__gte=window_started_at,
    ).count()
    return (
        request_count
        >= settings.RAG_MAX_REQUESTS_PER_WINDOW
    )


@login_required
@require_http_methods(["GET", "POST"])
def help_assistant(request):
    form = HelpAssistantForm(
        request.POST or None
    )
    result = None

    if request.method == "POST" and form.is_valid():
        if _rate_limit_exceeded(request.user):
            form.add_error(
                None,
                (
                    "You have reached the temporary Help Assistant limit. "
                    "Please wait a few minutes before trying again."
                ),
            )
        else:
            try:
                result = answer_question(
                    question=form.cleaned_data["question"],
                    user=request.user,
                )
            except AnswerGenerationError:
                form.add_error(
                    None,
                    (
                        "The Help Assistant could not generate an answer "
                        "right now. Please try again shortly."
                    ),
                )

    return render(
        request,
        "knowledge/help_assistant.html",
        {
            "form": form,
            "result": result,
        },
    )
