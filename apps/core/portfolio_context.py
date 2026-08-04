from __future__ import annotations

from django.conf import settings
from django.urls import reverse

from .portfolio_demo import is_portfolio_demo_user

STEP_DEFINITIONS = (
    (
        "dashboard",
        "Dashboard",
        "See readiness, due reviews, learning and evidence in one place.",
    ),
    (
        "plan",
        "Daily plan",
        "Inspect the selected work and why each task matters now.",
    ),
    (
        "roadmap",
        "User roadmap",
        "Explore the complete create, organise and focus workflow.",
    ),
    (
        "topic",
        "Topic workspace",
        "See notes, resources, progress, evidence and question generation.",
    ),
    (
        "question",
        "Question card",
        "Inspect a complete interview answer and spaced-review state.",
    ),
    (
        "evidence",
        "Project evidence",
        "Review architecture, decisions, trade-offs and a STAR story.",
    ),
    (
        "mock",
        "Mock interview",
        "Open a completed mixed interview and its self-assessment.",
    ),
    (
        "readiness",
        "Goal readiness",
        "See how learning and evidence connect to a target role.",
    ),
)


def _target_url(*, step_key: str, assets: dict):
    if step_key == "dashboard":
        return reverse("dashboard")
    if step_key == "plan":
        return reverse("planner:today")
    if step_key == "roadmap":
        return reverse(
            "roadmaps:custom_manage",
            kwargs={"slug": assets["custom_roadmap_slug"]},
        )
    if step_key == "topic":
        return reverse(
            "roadmaps:topic_detail",
            kwargs={
                "slug": assets["custom_roadmap_slug"],
                "topic_id": assets["featured_topic_id"],
            },
        )
    if step_key == "question":
        return reverse(
            "questions:detail",
            kwargs={"pk": assets["featured_question_id"]},
        )
    if step_key == "evidence":
        return reverse(
            "evidence:detail",
            kwargs={"evidence_id": assets["featured_evidence_id"]},
        )
    if step_key == "mock":
        return reverse(
            "interviews:summary",
            kwargs={"interview_id": assets["mock_interview_id"]},
        )
    if step_key == "readiness":
        return reverse(
            "goals:detail",
            kwargs={"goal_id": assets["goal_id"]},
        )
    raise KeyError(step_key)


def portfolio_demo_steps(request):
    assets = request.session.get("portfolio_demo_assets", {})
    completed = set(request.session.get("portfolio_demo_completed_steps", []))
    steps = []
    if not assets:
        return steps
    for key, label, description in STEP_DEFINITIONS:
        steps.append(
            {
                "key": key,
                "label": label,
                "description": description,
                "completed": key in completed,
                "launch_url": reverse(
                    "portfolio_demo_step",
                    kwargs={"step_key": key},
                ),
                "target_url": _target_url(step_key=key, assets=assets),
            }
        )
    return steps


def portfolio_demo_context(request):
    active = is_portfolio_demo_user(request.user)
    steps = portfolio_demo_steps(request) if active else []
    completed_count = sum(step["completed"] for step in steps)
    return {
        "portfolio_demo_enabled": settings.PORTFOLIO_DEMO_ENABLED,
        "portfolio_demo_active": active,
        "portfolio_demo_steps": steps,
        "portfolio_demo_completed_count": completed_count,
        "portfolio_demo_total_count": len(steps),
        "portfolio_demo_expires_at": request.session.get(
            "portfolio_demo_expires_at",
            "",
        ),
    }
