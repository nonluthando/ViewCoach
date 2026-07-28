"""Planner candidate domain objects.

Candidates are deliberately independent from Django models. Database-facing
services can build these immutable objects, then hand them to either the
heuristic selector or a future OR-Tools selector.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CandidateKind(StrEnum):
    REVIEW = "REVIEW"
    ROADMAP = "ROADMAP"
    WEAK_AREA = "WEAK_AREA"
    PRACTICE = "PRACTICE"
    LIBRARY = "LIBRARY"


@dataclass(frozen=True, slots=True)
class PlanCandidate:
    candidate_id: str
    kind: CandidateKind
    title: str
    estimated_minutes: int

    question_ids: tuple[int, ...] = ()
    roadmap_id: int | None = None
    topic_ids: tuple[int, ...] = ()
    goal_id: int | None = None
    context_key: str = ""

    is_overdue: bool = False
    is_recently_hard: bool = False
    supports_primary_goal: bool = False
    continues_in_progress_work: bool = False
    deadline_days: int | None = None

    description: str = ""
    rationale: str = ""

    def __post_init__(self):
        if not self.candidate_id.strip():
            raise ValueError("candidate_id must not be empty.")
        if not self.title.strip():
            raise ValueError("title must not be empty.")
        if self.estimated_minutes <= 0:
            raise ValueError("estimated_minutes must be positive.")
        if len(set(self.question_ids)) != len(self.question_ids):
            raise ValueError("question_ids must not contain duplicates.")
        if len(set(self.topic_ids)) != len(self.topic_ids):
            raise ValueError("topic_ids must not contain duplicates.")
        if self.kind == CandidateKind.ROADMAP and self.roadmap_id is None:
            raise ValueError("Roadmap candidates require roadmap_id.")
        if self.kind == CandidateKind.ROADMAP and not self.topic_ids:
            raise ValueError("Roadmap candidates require at least one topic_id.")

    @property
    def effective_context_key(self):
        if self.context_key:
            return self.context_key
        if self.roadmap_id is not None:
            return f"roadmap:{self.roadmap_id}"
        if self.question_ids:
            return f"{self.kind.value.lower()}:questions"
        return self.kind.value.lower()

    @property
    def topic_count(self):
        return len(self.topic_ids)


def stable_candidate_id(*, kind, source, source_ids):
    kind_value = CandidateKind(kind).value.lower()
    identifiers = "-".join(str(source_id) for source_id in source_ids)
    return f"{kind_value}:{source}:{identifiers}"
