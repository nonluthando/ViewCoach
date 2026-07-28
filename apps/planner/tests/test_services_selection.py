import pytest
from django.test import override_settings

from apps.planner.models import StudyPlan
from apps.planner.services import generate_daily_plan, plan_summary


pytestmark = pytest.mark.django_db


@override_settings(PLANNER_USE_OPTIMISER=False)
def test_plan_records_fallback_selection_metadata(user):
    plan = generate_daily_plan(
        user=user,
        time_budget_minutes=30,
    )

    assert plan.selection_status == StudyPlan.SelectionStatus.FALLBACK
    assert plan.selection_objective is None
    assert plan.selection_best_bound is None

    summary = plan_summary(plan=plan)
    assert summary["selection_status"] == "FALLBACK"
