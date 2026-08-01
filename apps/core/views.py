from django.contrib.auth.decorators import login_required
from django.db import OperationalError, connection
from django.http import JsonResponse
from django.shortcuts import render

from apps.evidence.services import evidence_dashboard_summary
from apps.goals.services import primary_goal_for_user, readiness_report
from apps.planner.services import generate_daily_plan, plan_summary
from apps.questions.models import Question
from apps.reviews.services import review_dashboard_summary
from apps.roadmaps.services import (
    grouped_viewcoach_roadmap_cards,
    youtube_roadmap_cards,
)


def landing_page(request):
    return render(request, "core/landing_page.html")


def _prioritised_learning_cards(groups, *, limit=2, focused_only=False):
    cards = [item for group in groups for item in group["items"]]
    if focused_only:
        cards = [
            item for item in cards if item["enrolment"] is not None and item["enrolment"].is_focused
        ]
    cards.sort(
        key=lambda item: (
            item["enrolment"] is None,
            -(item["percentage"] or 0),
            item["roadmap"].position,
            item["roadmap"].title,
        )
    )
    return cards[:limit]


@login_required
def dashboard(request):
    questions = Question.objects.filter(owner=request.user)
    review_summary = review_dashboard_summary(user=request.user)

    today_plan = plan_summary(plan=generate_daily_plan(user=request.user))
    primary_goal = primary_goal_for_user(user=request.user)
    readiness = readiness_report(goal=primary_goal) if primary_goal else None
    evidence_summary = evidence_dashboard_summary(user=request.user)
    viewcoach_groups = grouped_viewcoach_roadmap_cards(user=request.user)
    youtube_cards = youtube_roadmap_cards(user=request.user, favourites_only=True)

    return render(
        request,
        "core/dashboard.html",
        {
            "question_count": questions.count(),
            "ready_question_count": questions.filter(
                status=Question.Status.READY_FOR_REVIEW
            ).count(),
            "due_review_count": review_summary["due_count"],
            "reviewed_today_count": review_summary["reviewed_today_count"],
            "next_review_state": review_summary["next_state"],
            "today_plan": today_plan,
            "primary_goal": primary_goal,
            "readiness": readiness,
            "evidence_summary": evidence_summary,
            "viewcoach_learning_cards": _prioritised_learning_cards(
                viewcoach_groups,
                focused_only=True,
            ),
            "youtube_learning_cards": youtube_cards[:2],
            "recent_questions": questions.select_related(
                "technicalquestion",
                "conceptquestion",
                "behaviouralquestion",
                "debugquestion",
            )[:5],
        },
    )


@login_required
def learn(request):
    return render(request, "core/learn.html")


@login_required
def prepare(request):
    return render(request, "core/prepare.html")


@login_required
def interview(request):
    return render(request, "core/interview.html")


def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except OperationalError:
        return JsonResponse({"status": "unavailable"}, status=503)

    return JsonResponse({"status": "ok"})
