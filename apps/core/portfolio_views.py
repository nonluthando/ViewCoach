from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .portfolio_context import STEP_DEFINITIONS, portfolio_demo_steps
from .portfolio_demo import (
    cleanup_expired_portfolio_demo_users,
    create_portfolio_demo_workspace,
    delete_portfolio_demo_user,
    is_portfolio_demo_user,
    portfolio_demo_users,
)


def project_showcase(request):
    return render(request, "core/project_showcase.html")


def _activate_workspace(request, workspace):
    login(
        request,
        workspace.user,
        backend="django.contrib.auth.backends.ModelBackend",
    )
    request.session.set_expiry(settings.PORTFOLIO_DEMO_SESSION_SECONDS)
    started_at = timezone.now()
    request.session["portfolio_demo"] = True
    request.session["portfolio_demo_started_at"] = started_at.isoformat()
    request.session["portfolio_demo_expires_at"] = (
        started_at + timedelta(seconds=settings.PORTFOLIO_DEMO_SESSION_SECONDS)
    ).isoformat()
    request.session["portfolio_demo_assets"] = workspace.session_assets()
    request.session["portfolio_demo_completed_steps"] = []


@require_POST
def portfolio_demo_start(request):
    if not settings.PORTFOLIO_DEMO_ENABLED:
        raise Http404("The recruiter demo is not enabled.")

    if request.user.is_authenticated:
        if is_portfolio_demo_user(request.user):
            return redirect("portfolio_demo_guide")
        messages.info(
            request,
            "You are already signed in. Your own workspace remains separate.",
        )
        return redirect("dashboard")

    cleanup_expired_portfolio_demo_users()
    if portfolio_demo_users().count() >= settings.PORTFOLIO_DEMO_MAX_ACTIVE:
        return render(
            request,
            "core/portfolio_demo_unavailable.html",
            status=503,
        )

    workspace = create_portfolio_demo_workspace()
    _activate_workspace(request, workspace)
    messages.success(
        request,
        (
            "Your isolated recruiter demo is ready. Changes affect only this "
            "temporary workspace."
        ),
    )
    return redirect("portfolio_demo_guide")


@login_required
def portfolio_demo_guide(request):
    if not is_portfolio_demo_user(request.user):
        return redirect("project_showcase")
    return render(
        request,
        "core/portfolio_demo_guide.html",
        {"steps": portfolio_demo_steps(request)},
    )


@login_required
def portfolio_demo_step(request, step_key):
    if not is_portfolio_demo_user(request.user):
        return redirect("project_showcase")

    valid_keys = {key for key, _, _ in STEP_DEFINITIONS}
    if step_key not in valid_keys:
        raise Http404("Unknown demo step.")

    steps = {step["key"]: step for step in portfolio_demo_steps(request)}
    completed = list(request.session.get("portfolio_demo_completed_steps", []))
    if step_key not in completed:
        completed.append(step_key)
        request.session["portfolio_demo_completed_steps"] = completed
        request.session.modified = True
    return redirect(steps[step_key]["target_url"])


@login_required
@require_POST
def portfolio_demo_reset(request):
    if not is_portfolio_demo_user(request.user):
        raise Http404("No temporary demo workspace is active.")

    old_user_id = request.user.pk
    logout(request)
    delete_portfolio_demo_user(user_id=old_user_id)

    workspace = create_portfolio_demo_workspace()
    _activate_workspace(request, workspace)
    messages.success(request, "The demo was reset to its original seeded state.")
    return redirect("portfolio_demo_guide")


@login_required
@require_POST
def portfolio_demo_end(request):
    if not is_portfolio_demo_user(request.user):
        raise Http404("No temporary demo workspace is active.")

    user_id = request.user.pk
    logout(request)
    delete_portfolio_demo_user(user_id=user_id)
    messages.info(request, "The temporary demo workspace was deleted.")
    return redirect("project_showcase")
