"""OR-Tools CP-SAT candidate selector."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .candidates import CandidateKind
from .heuristic import CandidateRejection
from .policies import DailyPlanPolicy
from .scoring import ScoredCandidate, ranked_candidates

try:
    from ortools.sat.python import cp_model
except ImportError:  # pragma: no cover - exercised through selection fallback.
    cp_model = None


class OptimiserUnavailable(RuntimeError):
    pass


class OptimisationFailed(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class OptimisationResult:
    selected: tuple[ScoredCandidate, ...]
    rejected: tuple[CandidateRejection, ...]
    time_budget_minutes: int
    used_minutes: int
    status: str
    objective_value: float | None
    best_bound: float | None
    solve_time_ms: int | None

    @property
    def unused_minutes(self):
        return max(0, self.time_budget_minutes - self.used_minutes)

    @property
    def selected_candidates(self):
        return tuple(item.candidate for item in self.selected)


def optimiser_available():
    return cp_model is not None


def _group_indices(ranked, values):
    grouped = defaultdict(list)
    for index, scored_candidate in enumerate(ranked):
        for value in values(scored_candidate.candidate):
            grouped[value].append(index)
    return grouped


def optimise_candidates(
    *,
    candidates,
    policy,
    time_budget_minutes=None,
    time_limit_seconds=0.25,
):
    if cp_model is None:
        raise OptimiserUnavailable("OR-Tools is not installed; use the heuristic fallback.")
    if not isinstance(policy, DailyPlanPolicy):
        raise TypeError("policy must be a DailyPlanPolicy.")

    budget = (
        policy.time_budget_minutes
        if time_budget_minutes is None
        else max(1, int(time_budget_minutes))
    )
    ranked = ranked_candidates(candidates)
    if not ranked:
        return OptimisationResult(
            selected=(),
            rejected=(),
            time_budget_minutes=budget,
            used_minutes=0,
            status="OPTIMAL",
            objective_value=0.0,
            best_bound=0.0,
            solve_time_ms=0,
        )

    candidate_ids = [item.candidate.candidate_id for item in ranked]
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("Candidate identifiers must be unique.")

    model = cp_model.CpModel()
    selected_vars = [
        model.new_bool_var(f"candidate_{index}")
        for index in range(len(ranked))
    ]

    for index, item in enumerate(ranked):
        if item.candidate.is_required:
            model.add(selected_vars[index] == 1)

    model.add(
        sum(
            item.candidate.estimated_minutes * selected_vars[index]
            for index, item in enumerate(ranked)
        )
        <= budget
    )

    question_indices = _group_indices(
        ranked,
        lambda candidate: candidate.question_ids,
    )
    for indices in question_indices.values():
        model.add(sum(selected_vars[index] for index in indices) <= 1)

    topic_indices = _group_indices(
        ranked,
        lambda candidate: candidate.topic_ids,
    )
    for indices in topic_indices.values():
        model.add(sum(selected_vars[index] for index in indices) <= 1)

    roadmap_indices = defaultdict(list)
    for index, item in enumerate(ranked):
        candidate = item.candidate
        if candidate.kind == CandidateKind.ROADMAP and candidate.roadmap_id is not None:
            roadmap_indices[candidate.roadmap_id].append(index)

    roadmap_vars = {}
    for roadmap_id, indices in roadmap_indices.items():
        roadmap_var = model.new_bool_var(f"roadmap_{roadmap_id}")
        roadmap_vars[roadmap_id] = roadmap_var
        for index in indices:
            model.add(selected_vars[index] <= roadmap_var)
        model.add(roadmap_var <= sum(selected_vars[index] for index in indices))
        model.add(
            sum(ranked[index].candidate.topic_count * selected_vars[index] for index in indices)
            <= policy.max_topics_per_roadmap
        )

    if roadmap_vars:
        model.add(sum(roadmap_vars.values()) <= policy.max_roadmaps)

    review_indices = [
        index for index, item in enumerate(ranked) if item.candidate.kind == CandidateKind.REVIEW
    ]
    if review_indices:
        model.add(
            sum(
                ranked[index].candidate.estimated_minutes * selected_vars[index]
                for index in review_indices
            )
            <= policy.review_target_minutes
        )

    practice_indices = [
        index
        for index, item in enumerate(ranked)
        if item.candidate.kind in {CandidateKind.PRACTICE, CandidateKind.WEAK_AREA}
    ]
    if practice_indices:
        model.add(
            sum(
                ranked[index].candidate.estimated_minutes * selected_vars[index]
                for index in practice_indices
            )
            <= policy.practice_target_minutes
        )

    pure_practice_indices = [
        index for index, item in enumerate(ranked) if item.candidate.kind == CandidateKind.PRACTICE
    ]
    if pure_practice_indices:
        model.add(
            sum(selected_vars[index] for index in pure_practice_indices)
            <= policy.max_practice_blocks
        )

    weak_indices = [
        index for index, item in enumerate(ranked) if item.candidate.kind == CandidateKind.WEAK_AREA
    ]
    if weak_indices:
        model.add(
            sum(selected_vars[index] for index in weak_indices)
            <= policy.max_weak_area_blocks
        )

    readiness_indices = [
        index
        for index, item in enumerate(ranked)
        if item.candidate.kind
        in {
            CandidateKind.EVIDENCE,
            CandidateKind.GUIDE,
            CandidateKind.MOCK,
        }
    ]
    if readiness_indices:
        model.add(
            sum(selected_vars[index] for index in readiness_indices)
            <= policy.max_readiness_blocks
        )

    context_indices = _group_indices(
        ranked,
        lambda candidate: (candidate.effective_context_key,),
    )
    context_vars = {}
    for context_position, (context_key, indices) in enumerate(sorted(context_indices.items())):
        context_var = model.new_bool_var(f"context_{context_position}")
        context_vars[context_key] = context_var
        for index in indices:
            model.add(selected_vars[index] <= context_var)
        model.add(context_var <= sum(selected_vars[index] for index in indices))

    score_term = sum(
        item.total_score * 100 * selected_vars[index] for index, item in enumerate(ranked)
    )
    used_minutes_term = sum(
        item.candidate.estimated_minutes * selected_vars[index] for index, item in enumerate(ranked)
    )
    context_switch_penalty = 300 * sum(context_vars.values()) if context_vars else 0
    model.maximize(score_term + used_minutes_term - context_switch_penalty)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(
        0.01,
        float(time_limit_seconds),
    )
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0

    solver_status = solver.solve(model)
    if solver_status == cp_model.OPTIMAL:
        status = "OPTIMAL"
    elif solver_status == cp_model.FEASIBLE:
        status = "FEASIBLE"
    else:
        raise OptimisationFailed(f"CP-SAT returned status {solver.status_name(solver_status)}.")

    selected = tuple(
        item for index, item in enumerate(ranked) if solver.value(selected_vars[index])
    )
    selected_ids = {item.candidate.candidate_id for item in selected}
    rejected = tuple(
        CandidateRejection(
            candidate_id=item.candidate.candidate_id,
            reason="not selected by the optimiser",
        )
        for item in ranked
        if item.candidate.candidate_id not in selected_ids
    )
    used_minutes = sum(item.candidate.estimated_minutes for item in selected)

    return OptimisationResult(
        selected=selected,
        rejected=rejected,
        time_budget_minutes=budget,
        used_minutes=used_minutes,
        status=status,
        objective_value=float(solver.objective_value),
        best_bound=float(solver.best_objective_bound),
        solve_time_ms=max(0, round(solver.wall_time * 1000)),
    )
