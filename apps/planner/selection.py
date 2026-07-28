"""Choose CP-SAT when available and fall back to the deterministic heuristic."""

from __future__ import annotations

from dataclasses import dataclass

from .heuristic import CandidateRejection, select_candidates
from .optimisation import (
    OptimisationFailed,
    OptimiserUnavailable,
    optimise_candidates,
)
from .scoring import ScoredCandidate


@dataclass(frozen=True, slots=True)
class PlannerSelectionResult:
    selected: tuple[ScoredCandidate, ...]
    rejected: tuple[CandidateRejection, ...]
    time_budget_minutes: int
    used_minutes: int
    status: str
    objective_value: float | None = None
    best_bound: float | None = None
    solve_time_ms: int | None = None

    @property
    def unused_minutes(self):
        return max(0, self.time_budget_minutes - self.used_minutes)

    @property
    def selected_candidates(self):
        return tuple(item.candidate for item in self.selected)


def _fallback_result(*, candidates, policy, time_budget_minutes):
    fallback = select_candidates(
        candidates=candidates,
        policy=policy,
        time_budget_minutes=time_budget_minutes,
    )
    return PlannerSelectionResult(
        selected=fallback.selected,
        rejected=fallback.rejected,
        time_budget_minutes=fallback.time_budget_minutes,
        used_minutes=fallback.used_minutes,
        status="FALLBACK",
    )


def select_plan_candidates(
    *,
    candidates,
    policy,
    time_budget_minutes=None,
    use_optimiser=True,
    time_limit_seconds=0.25,
):
    budget = (
        policy.time_budget_minutes
        if time_budget_minutes is None
        else max(1, int(time_budget_minutes))
    )

    if use_optimiser:
        try:
            optimised = optimise_candidates(
                candidates=candidates,
                policy=policy,
                time_budget_minutes=budget,
                time_limit_seconds=time_limit_seconds,
            )
        except (OptimiserUnavailable, OptimisationFailed):
            return _fallback_result(
                candidates=candidates,
                policy=policy,
                time_budget_minutes=budget,
            )

        return PlannerSelectionResult(
            selected=optimised.selected,
            rejected=optimised.rejected,
            time_budget_minutes=optimised.time_budget_minutes,
            used_minutes=optimised.used_minutes,
            status=optimised.status,
            objective_value=optimised.objective_value,
            best_bound=optimised.best_bound,
            solve_time_ms=optimised.solve_time_ms,
        )

    return _fallback_result(
        candidates=candidates,
        policy=policy,
        time_budget_minutes=budget,
    )
