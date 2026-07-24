from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import InterviewGoalForm, InterviewStageForm
from .models import InterviewGoal, InterviewStage
from .services import (
    complete_stage,
    ensure_primary_goal,
    readiness_report,
    set_current_stage,
    set_goal_status,
    set_primary_goal,
    sync_goal_roadmap,
)


def _owned_goals(user):
    return InterviewGoal.objects.filter(user=user).select_related("roadmap")


def _owned_goal(user, goal_id):
    return get_object_or_404(_owned_goals(user).prefetch_related("stages"), pk=goal_id)


@login_required
def goal_list(request):
    goals = _owned_goals(request.user)
    return render(
        request,
        "goals/goal_list.html",
        {
            "active_goals": goals.filter(status=InterviewGoal.Status.ACTIVE),
            "inactive_goals": goals.exclude(status=InterviewGoal.Status.ACTIVE),
        },
    )


@login_required
def goal_create(request):
    if request.method == "POST":
        form = InterviewGoalForm(request.POST, user=request.user)
        if form.is_valid():
            make_primary = form.cleaned_data["is_primary"]
            goal = form.save(commit=False)
            goal.user = request.user
            goal.is_primary = False
            goal.save()
            if make_primary:
                set_primary_goal(goal=goal)
            else:
                ensure_primary_goal(goal=goal)
            sync_goal_roadmap(goal=goal)
            messages.success(request, "Interview goal created.")
            return redirect(goal)
    else:
        form = InterviewGoalForm(user=request.user)
    return render(
        request,
        "goals/goal_form.html",
        {"form": form, "is_editing": False},
    )


@login_required
def goal_edit(request, goal_id):
    goal = _owned_goal(request.user, goal_id)
    if request.method == "POST":
        form = InterviewGoalForm(
            request.POST,
            instance=goal,
            user=request.user,
        )
        if form.is_valid():
            make_primary = form.cleaned_data["is_primary"]
            goal = form.save(commit=False)
            goal.is_primary = False
            goal.save()
            if make_primary:
                set_primary_goal(goal=goal)
            else:
                ensure_primary_goal(goal=goal)
            sync_goal_roadmap(goal=goal)
            messages.success(request, "Interview goal updated.")
            return redirect(goal)
    else:
        form = InterviewGoalForm(instance=goal, user=request.user)
    return render(
        request,
        "goals/goal_form.html",
        {"form": form, "goal": goal, "is_editing": True},
    )


@login_required
def goal_detail(request, goal_id):
    goal = _owned_goal(request.user, goal_id)
    return render(
        request,
        "goals/goal_detail.html",
        {
            "goal": goal,
            "report": readiness_report(goal=goal),
            "stage_form": InterviewStageForm(),
            "status_choices": InterviewGoal.Status.choices,
        },
    )


@login_required
@require_POST
def goal_set_primary(request, goal_id):
    goal = _owned_goal(request.user, goal_id)
    try:
        set_primary_goal(goal=goal)
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"{goal.title} is now your primary goal.")
    return redirect(goal)


@login_required
@require_POST
def goal_update_status(request, goal_id):
    goal = _owned_goal(request.user, goal_id)
    try:
        set_goal_status(goal=goal, status=request.POST.get("status", ""))
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Goal status updated.")
    return redirect(goal)


@login_required
@require_POST
def stage_add(request, goal_id):
    goal = _owned_goal(request.user, goal_id)
    form = InterviewStageForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Check the stage details and try again.")
        return render(
            request,
            "goals/goal_detail.html",
            {
                "goal": goal,
                "report": readiness_report(goal=goal),
                "stage_form": form,
                "status_choices": InterviewGoal.Status.choices,
            },
            status=400,
        )

    make_current = form.cleaned_data["is_current"]
    stage = form.save(commit=False)
    stage.goal = goal
    stage.position = goal.stages.count() + 1
    stage.is_current = False
    stage.save()
    if make_current or goal.current_stage is None:
        set_current_stage(stage=stage)
    sync_goal_roadmap(goal=goal)
    messages.success(request, "Interview stage added.")
    return redirect(goal)


@login_required
@require_POST
def stage_set_current(request, goal_id, stage_id):
    goal = _owned_goal(request.user, goal_id)
    stage = get_object_or_404(InterviewStage, goal=goal, pk=stage_id)
    try:
        set_current_stage(stage=stage)
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Next interview stage updated.")
    return redirect(goal)


@login_required
@require_POST
def stage_complete(request, goal_id, stage_id):
    goal = _owned_goal(request.user, goal_id)
    stage = get_object_or_404(InterviewStage, goal=goal, pk=stage_id)
    complete_stage(stage=stage)
    messages.success(request, "Interview stage completed.")
    return redirect(goal)
