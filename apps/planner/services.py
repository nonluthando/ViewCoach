from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .candidate_builders import (
    build_plan_candidates,
    recommendation_payloads_from_selection,
)
from .models import StudyPlan, StudyRecommendation, StudySession
from .selection import select_plan_candidates


DEFAULT_TIME_BUDGET_MINUTES = 60


def _payloads_and_selection(
    *,
    user,
    time_budget_minutes,
    plan_date,
    now,
):
    build_result = build_plan_candidates(
        user=user,
        time_budget_minutes=time_budget_minutes,
        plan_date=plan_date,
        now=now,
    )
    selection_result = select_plan_candidates(
        candidates=build_result.candidates,
        policy=build_result.policy,
        time_budget_minutes=time_budget_minutes,
        use_optimiser=getattr(
            settings,
            "PLANNER_USE_OPTIMISER",
            True,
        ),
        time_limit_seconds=getattr(
            settings,
            "PLANNER_OPTIMISER_TIME_LIMIT_SECONDS",
            0.25,
        ),
    )
    payloads = recommendation_payloads_from_selection(
        build_result=build_result,
        selection_result=selection_result,
        time_budget_minutes=time_budget_minutes,
    )
    return payloads, selection_result


def _recommendation_payloads(
    *,
    user,
    time_budget_minutes,
    plan_date,
    now,
):
    payloads, _ = _payloads_and_selection(
        user=user,
        time_budget_minutes=time_budget_minutes,
        plan_date=plan_date,
        now=now,
    )
    return payloads


@transaction.atomic
def generate_daily_plan(
    *,
    user,
    time_budget_minutes=DEFAULT_TIME_BUDGET_MINUTES,
    now=None,
    force=False,
):
    current_time = now or timezone.now()
    plan_date = timezone.localdate(current_time)
    plan, created = StudyPlan.objects.select_for_update().get_or_create(
        user=user,
        plan_date=plan_date,
        defaults={
            "time_budget_minutes": time_budget_minutes,
            "generated_at": current_time,
        },
    )

    should_regenerate = (
        created
        or force
        or not plan.recommendations.exists()
    )
    if not should_regenerate:
        return plan

    payloads, selection_result = _payloads_and_selection(
        user=user,
        time_budget_minutes=time_budget_minutes,
        plan_date=plan_date,
        now=current_time,
    )

    plan.recommendations.all().delete()
    plan.time_budget_minutes = time_budget_minutes
    plan.status = StudyPlan.Status.ACTIVE
    plan.selection_status = selection_result.status
    plan.selection_objective = selection_result.objective_value
    plan.selection_best_bound = selection_result.best_bound
    plan.selection_solve_time_ms = selection_result.solve_time_ms
    plan.generated_at = current_time
    plan.save(
        update_fields=[
            "time_budget_minutes",
            "status",
            "selection_status",
            "selection_objective",
            "selection_best_bound",
            "selection_solve_time_ms",
            "generated_at",
            "updated_at",
        ]
    )

    StudyRecommendation.objects.bulk_create(
        [
            StudyRecommendation(
                plan=plan,
                position=position,
                **payload,
            )
            for position, payload in enumerate(payloads, start=1)
        ]
    )
    return plan


def plan_summary(*, plan):
    recommendations = list(
        plan.recommendations.select_related(
            "question",
            "topic__section__roadmap",
        )
    )
    completed_count = sum(
        recommendation.completed_at is not None
        for recommendation in recommendations
    )
    return {
        "plan": plan,
        "recommendations": recommendations,
        "total_count": len(recommendations),
        "completed_count": completed_count,
        "estimated_minutes": sum(
            recommendation.estimated_minutes
            for recommendation in recommendations
        ),
        "is_complete": (
            bool(recommendations)
            and completed_count == len(recommendations)
        ),
        "selection_status": plan.selection_status,
        "selection_objective": plan.selection_objective,
        "selection_best_bound": plan.selection_best_bound,
        "selection_solve_time_ms": plan.selection_solve_time_ms,
    }


def sync_plan_status(*, plan):
    recommendations = plan.recommendations.all()
    has_recommendations = recommendations.exists()
    is_complete = (
        has_recommendations
        and not recommendations.filter(
            completed_at__isnull=True
        ).exists()
    )
    new_status = (
        StudyPlan.Status.COMPLETED
        if is_complete
        else StudyPlan.Status.ACTIVE
    )
    if plan.status != new_status:
        plan.status = new_status
        plan.save(update_fields=["status", "updated_at"])
    return plan


@transaction.atomic
def toggle_recommendation_completion(*, recommendation, now=None):
    locked_recommendation = (
        StudyRecommendation.objects.select_for_update().get(
            pk=recommendation.pk
        )
    )
    locked_recommendation.completed_at = (
        None
        if locked_recommendation.completed_at
        else (now or timezone.now())
    )
    locked_recommendation.save(update_fields=["completed_at"])
    sync_plan_status(plan=locked_recommendation.plan)
    return locked_recommendation


@transaction.atomic
def start_study_session(*, plan, now=None):
    active_session = plan.sessions.filter(
        ended_at__isnull=True
    ).first()
    if active_session is not None:
        return active_session, False

    session = StudySession.objects.create(
        plan=plan,
        started_at=now or timezone.now(),
    )
    return session, True


@transaction.atomic
def finish_study_session(*, session, now=None):
    locked_session = StudySession.objects.select_for_update().get(
        pk=session.pk
    )
    if locked_session.ended_at is not None:
        return locked_session

    locked_session.ended_at = now or timezone.now()
    locked_session.completed_recommendation_count = (
        locked_session.plan.recommendations.filter(
            completed_at__isnull=False
        ).count()
    )
    locked_session.save(
        update_fields=[
            "ended_at",
            "completed_recommendation_count",
        ]
    )
    sync_plan_status(plan=locked_session.plan)
    return locked_session
