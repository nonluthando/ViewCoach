from apps.planner.candidates import CandidateKind, PlanCandidate
from apps.planner.optimisation import OptimiserUnavailable
from apps.planner.policies import plan_policy_for_budget
from apps.planner.selection import select_plan_candidates


def _practice_candidate():
    return PlanCandidate(
        candidate_id="practice:1",
        kind=CandidateKind.PRACTICE,
        title="Practice arrays",
        estimated_minutes=15,
        question_ids=(1,),
    )


def test_selection_can_disable_optimiser():
    policy = plan_policy_for_budget(
        time_budget_minutes=30,
        due_count=0,
    )

    result = select_plan_candidates(
        candidates=[_practice_candidate()],
        policy=policy,
        use_optimiser=False,
    )

    assert result.status == "FALLBACK"
    assert len(result.selected) == 1


def test_selection_falls_back_when_optimiser_is_unavailable(
    monkeypatch,
):
    policy = plan_policy_for_budget(
        time_budget_minutes=30,
        due_count=0,
    )

    def unavailable(**kwargs):
        raise OptimiserUnavailable("not installed")

    monkeypatch.setattr(
        "apps.planner.selection.optimise_candidates",
        unavailable,
    )

    result = select_plan_candidates(
        candidates=[_practice_candidate()],
        policy=policy,
        use_optimiser=True,
    )

    assert result.status == "FALLBACK"
    assert len(result.selected) == 1
