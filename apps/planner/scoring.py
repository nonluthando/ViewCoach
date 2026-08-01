"""Deterministic, explainable candidate scoring."""

from __future__ import annotations

from dataclasses import dataclass

from .candidates import CandidateKind, PlanCandidate

BASE_SCORE_BY_KIND = {
    CandidateKind.REVIEW: 100,
    CandidateKind.ROADMAP: 80,
    CandidateKind.WEAK_AREA: 70,
    CandidateKind.PRACTICE: 50,
    CandidateKind.LIBRARY: 20,
}

KIND_ORDER = {
    CandidateKind.REVIEW: 0,
    CandidateKind.ROADMAP: 1,
    CandidateKind.WEAK_AREA: 2,
    CandidateKind.PRACTICE: 3,
    CandidateKind.LIBRARY: 4,
}


@dataclass(frozen=True, slots=True)
class ScoreComponent:
    key: str
    points: int
    explanation: str


@dataclass(frozen=True, slots=True)
class ScoredCandidate:
    candidate: PlanCandidate
    components: tuple[ScoreComponent, ...]

    @property
    def total_score(self):
        return sum(component.points for component in self.components)


def _deadline_component(deadline_days):
    if deadline_days is None or deadline_days < 0:
        return None
    if deadline_days <= 3:
        return ScoreComponent(
            key="deadline_urgent",
            points=20,
            explanation="A linked deadline is within three days.",
        )
    if deadline_days <= 7:
        return ScoreComponent(
            key="deadline_near",
            points=15,
            explanation="A linked deadline is within one week.",
        )
    if deadline_days <= 14:
        return ScoreComponent(
            key="deadline_upcoming",
            points=10,
            explanation="A linked deadline is within two weeks.",
        )
    return None


def score_candidate(candidate):
    if not isinstance(candidate, PlanCandidate):
        raise TypeError("candidate must be a PlanCandidate.")

    components = [
        ScoreComponent(
            key="kind_base",
            points=BASE_SCORE_BY_KIND[candidate.kind],
            explanation={
                CandidateKind.REVIEW: "Due review work receives first priority.",
                CandidateKind.ROADMAP: "Focused roadmap learning advances active study.",
                CandidateKind.WEAK_AREA: "Recent difficulty makes this useful recovery work.",
                CandidateKind.PRACTICE: "Fresh practice strengthens retrieval and application.",
                CandidateKind.LIBRARY: "Library preparation supports later study sessions.",
            }[candidate.kind],
        )
    ]

    if candidate.is_overdue:
        components.append(
            ScoreComponent(
                key="overdue",
                points=20,
                explanation="The work is already overdue.",
            )
        )

    if candidate.is_recently_hard:
        components.append(
            ScoreComponent(
                key="recently_hard",
                points=15,
                explanation="Recent performance was rated Again or Hard.",
            )
        )

    if candidate.supports_primary_goal:
        components.append(
            ScoreComponent(
                key="primary_goal",
                points=10,
                explanation="The work supports the primary interview goal.",
            )
        )

    if candidate.continues_in_progress_work:
        components.append(
            ScoreComponent(
                key="continuity",
                points=8,
                explanation="It continues work that is already in progress.",
            )
        )

    deadline_component = _deadline_component(candidate.deadline_days)
    if deadline_component is not None:
        components.append(deadline_component)

    return ScoredCandidate(
        candidate=candidate,
        components=tuple(components),
    )


def ranked_candidates(candidates):
    scored = [score_candidate(candidate) for candidate in candidates]
    return sorted(
        scored,
        key=lambda item: (
            -item.total_score,
            KIND_ORDER[item.candidate.kind],
            item.candidate.estimated_minutes,
            item.candidate.candidate_id,
        ),
    )
