from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import StudyPlanPreferencesForm
from .models import StudyRecommendation
from .services import (
    finish_study_session,
    generate_daily_plan,
    plan_summary,
    start_study_session,
    toggle_recommendation_completion,
)


def _today_plan_for_user(user):
    return generate_daily_plan(user=user)


@login_required
def today_plan(request):
    plan = _today_plan_for_user(request.user)
    summary = plan_summary(plan=plan)
    active_session = plan.sessions.filter(ended_at__isnull=True).first()
    form = StudyPlanPreferencesForm(
        initial={"time_budget_minutes": plan.time_budget_minutes}
    )
    return render(
        request,
        "planner/today.html",
        {
            **summary,
            "active_session": active_session,
            "preferences_form": form,
        },
    )


@login_required
@require_POST
def regenerate_plan(request):
    plan = _today_plan_for_user(request.user)
    if plan.sessions.filter(ended_at__isnull=True).exists():
        messages.warning(request, "End the active study session before rebuilding the plan.")
        return redirect("planner:today")

    form = StudyPlanPreferencesForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Choose a valid amount of study time.")
        return redirect("planner:today")

    generate_daily_plan(
        user=request.user,
        time_budget_minutes=form.cleaned_data["time_budget_minutes"],
        force=True,
    )
    messages.success(request, "Today’s plan was rebuilt around your available time.")
    return redirect("planner:today")


@login_required
@require_POST
def toggle_recommendation(request, recommendation_id):
    recommendation = get_object_or_404(
        StudyRecommendation.objects.select_related("plan"),
        pk=recommendation_id,
        plan__user=request.user,
    )
    updated = toggle_recommendation_completion(recommendation=recommendation)
    message = "Marked complete." if updated.completed_at else "Moved back into today’s plan."
    messages.success(request, message)
    return redirect("planner:today")


@login_required
@require_POST
def start_session(request):
    plan = _today_plan_for_user(request.user)
    _, created = start_study_session(plan=plan)
    if created:
        messages.success(request, "Study session started.")
    else:
        messages.info(request, "A study session is already running.")
    return redirect("planner:today")


@login_required
@require_POST
def finish_session(request):
    plan = _today_plan_for_user(request.user)
    session = plan.sessions.filter(ended_at__isnull=True).first()
    if session is None:
        messages.info(request, "There is no active study session to end.")
        return redirect("planner:today")

    finished_session = finish_study_session(session=session)
    messages.success(
        request,
        (
            "Study session ended after "
            f"{finished_session.duration_minutes} minute"
            f"{'s' if finished_session.duration_minutes != 1 else ''}."
        ),
    )
    return redirect("planner:today")
