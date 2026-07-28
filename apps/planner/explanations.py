"""Human-readable planner explanations."""

from __future__ import annotations

from .heuristic import CandidateRejection, SelectionResult
from .scoring import ScoredCandidate


def candidate_explanation(scored_candidate, *, max_reasons=3):
    if not isinstance(scored_candidate, ScoredCandidate):
        raise TypeError("scored_candidate must be a ScoredCandidate.")

    ordered_components = sorted(
        scored_candidate.components,
        key=lambda component: (-component.points, component.key),
    )
    explanations = [
        component.explanation
        for component in ordered_components
        if component.points > 0
    ][:max_reasons]

    candidate = scored_candidate.candidate
    if candidate.rationale.strip():
        explanations.append(candidate.rationale.strip())

    return " ".join(explanations)


def rejection_explanation(rejection):
    if not isinstance(rejection, CandidateRejection):
        raise TypeError("rejection must be a CandidateRejection.")
    return f"{rejection.candidate_id} was not selected: {rejection.reason}."


def selection_summary(result):
    if not isinstance(result, SelectionResult):
        raise TypeError("result must be a SelectionResult.")

    selected_count = len(result.selected)
    task_label = "task" if selected_count == 1 else "tasks"
    return (
        f"Selected {selected_count} {task_label} using "
        f"{result.used_minutes} of {result.time_budget_minutes} minutes. "
        f"{result.unused_minutes} minutes remain unallocated."
    )


def selected_candidate_explanations(result):
    if not isinstance(result, SelectionResult):
        raise TypeError("result must be a SelectionResult.")

    return tuple(
        {
            "candidate_id": item.candidate.candidate_id,
            "title": item.candidate.title,
            "score": item.total_score,
            "explanation": candidate_explanation(item),
        }
        for item in result.selected
    )
