from django.contrib.auth.decorators import login_required
from django.db import OperationalError, connection
from django.http import JsonResponse
from django.shortcuts import render

from apps.questions.models import Question
from apps.reviews.services import review_dashboard_summary


def landing_page(request):
    return render(request, "core/landing_page.html")


@login_required
def dashboard(request):
    questions = Question.objects.filter(owner=request.user)
    review_summary = review_dashboard_summary(user=request.user)

    return render(
        request,
        "core/dashboard.html",
        {
            "question_count": questions.count(),
            "ready_question_count": questions.filter(
                status=Question.Status.READY_FOR_REVIEW
            ).count(),
            "due_review_count": review_summary["due_count"],
            "reviewed_today_count": review_summary[
                "reviewed_today_count"
            ],
            "next_review_state": review_summary["next_state"],
            "recent_questions": questions.select_related(
                "technicalquestion",
                "conceptquestion",
                "behaviouralquestion",
                "debugquestion",
            )[:5],
        },
    )


def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except OperationalError:
        return JsonResponse({"status": "unavailable"}, status=503)

    return JsonResponse({"status": "ok"})
