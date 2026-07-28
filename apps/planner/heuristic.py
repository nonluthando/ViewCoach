"""Constraint-aware deterministic fallback selector.

The heuristic keeps the same candidate boundary that the later CP-SAT
implementation will consume. It therefore remains a safe fallback when the
optimiser is unavailable or cannot find a solution quickly.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .candidates import CandidateKind, PlanCandidate
from .policies import DailyPlanPolicy
from .scoring import ScoredCandidate, ranked_candidates


@dataclass(frozen=True, slots=True)
class CandidateRejection:
    candidate_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class SelectionResult:
    selected: tuple[ScoredCandidate, ...]
    rejected: tuple[CandidateRejection, ...]
    time_budget_minutes: int
    used_minutes: int
    status: str = "HEURISTIC"

    @property
    def unused_minutes(self):
        return max(0, self.time_budget_minutes - self.used_minutes)

    @property
    def selected_candidates(self):
        return tuple(item.candidate for item in self.selected)


class _SelectionState:
    def __init__(self, *, time_budget_minutes):
        self.time_budget_minutes = time_budget_minutes
        self.used_minutes = 0
        self.question_ids = set()
        self.roadmap_ids = set()
        self.topic_count_by_roadmap = defaultdict(int)
        self.practice_blocks = 0
        self.weak_area_blocks = 0
        self.selected_ids = set()
        self.last_context_key = ""

    @property
    def remaining_minutes(self):
        return self.time_budget_minutes - self.used_minutes


def _constraint_failure(*, candidate, state, policy):
    if candidate.candidate_id in state.selected_ids:
        return "duplicate candidate"

    if candidate.estimated_minutes > state.remaining_minutes:
        return "insufficient remaining time"

    if state.question_ids.intersection(candidate.question_ids):
        return "duplicates a selected question"

    if candidate.kind == CandidateKind.ROADMAP:
        is_new_roadmap = candidate.roadmap_id not in state.roadmap_ids
        if is_new_roadmap and len(state.roadmap_ids) >= policy.max_roadmaps:
            return "daily roadmap limit reached"

        current_topic_count = state.topic_count_by_roadmap[candidate.roadmap_id]
        if (
            current_topic_count + candidate.topic_count
            > policy.max_topics_per_roadmap
        ):
            return "topic limit reached for this roadmap"

    if (
        candidate.kind == CandidateKind.PRACTICE
        and state.practice_blocks >= policy.max_practice_blocks
    ):
        return "daily practice-block limit reached"

    if (
        candidate.kind == CandidateKind.WEAK_AREA
        and state.weak_area_blocks >= policy.max_weak_area_blocks
    ):
        return "daily weak-area limit reached"

    return ""


def _select(*, scored_candidate, state):
    candidate = scored_candidate.candidate
    state.selected_ids.add(candidate.candidate_id)
    state.used_minutes += candidate.estimated_minutes
    state.question_ids.update(candidate.question_ids)

    if candidate.kind == CandidateKind.ROADMAP:
        state.roadmap_ids.add(candidate.roadmap_id)
        state.topic_count_by_roadmap[candidate.roadmap_id] += candidate.topic_count
    elif candidate.kind == CandidateKind.PRACTICE:
        state.practice_blocks += 1
    elif candidate.kind == CandidateKind.WEAK_AREA:
        state.weak_area_blocks += 1

    state.last_context_key = candidate.effective_context_key


def _context_adjusted_order(scored_candidates, state):
    return sorted(
        scored_candidates,
        key=lambda item: (
            -(
                item.total_score
                + (
                    5
                    if state.last_context_key
                    and item.candidate.effective_context_key
                    == state.last_context_key
                    else 0
                )
            ),
            item.candidate.estimated_minutes,
            item.candidate.candidate_id,
        ),
    )


def _choose_from_pass(*, candidates, state, policy, selected, rejected):
    remaining = list(candidates)
    while remaining:
        ordered = _context_adjusted_order(remaining, state)
        scored_candidate = ordered[0]
        remaining.remove(scored_candidate)

        reason = _constraint_failure(
            candidate=scored_candidate.candidate,
            state=state,
            policy=policy,
        )
        if reason:
            rejected.append(
                CandidateRejection(
                    candidate_id=scored_candidate.candidate.candidate_id,
                    reason=reason,
                )
            )
            continue

        _select(scored_candidate=scored_candidate, state=state)
        selected.append(scored_candidate)


def select_candidates(*, candidates, policy, time_budget_minutes=None):
    if not isinstance(policy, DailyPlanPolicy):
        raise TypeError("policy must be a DailyPlanPolicy.")

    budget = (
        policy.time_budget_minutes
        if time_budget_minutes is None
        else max(1, int(time_budget_minutes))
    )
    ranked = ranked_candidates(candidates)
    state = _SelectionState(time_budget_minutes=budget)
    selected = []
    rejected = []

    review_candidates = [
        item for item in ranked if item.candidate.kind == CandidateKind.REVIEW
    ]
    roadmap_candidates = [
        item for item in ranked if item.candidate.kind == CandidateKind.ROADMAP
    ]
    remaining_candidates = [
        item
        for item in ranked
        if item.candidate.kind
        not in {CandidateKind.REVIEW, CandidateKind.ROADMAP}
    ]

    _choose_from_pass(
        candidates=review_candidates,
        state=state,
        policy=policy,
        selected=selected,
        rejected=rejected,
    )
    _choose_from_pass(
        candidates=roadmap_candidates,
        state=state,
        policy=policy,
        selected=selected,
        rejected=rejected,
    )
    _choose_from_pass(
        candidates=remaining_candidates,
        state=state,
        policy=policy,
        selected=selected,
        rejected=rejected,
    )

    return SelectionResult(
        selected=tuple(selected),
        rejected=tuple(rejected),
        time_budget_minutes=budget,
        used_minutes=state.used_minutes,
    )
