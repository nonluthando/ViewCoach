import pytest

from apps.planner.candidates import (
    CandidateKind,
    PlanCandidate,
    stable_candidate_id,
)


def test_roadmap_candidate_requires_topic_and_roadmap():
    with pytest.raises(ValueError):
        PlanCandidate(
            candidate_id="roadmap:missing",
            kind=CandidateKind.ROADMAP,
            title="Learn SQL",
            estimated_minutes=45,
        )


def test_candidate_rejects_duplicate_question_ids():
    with pytest.raises(ValueError):
        PlanCandidate(
            candidate_id="review:duplicates",
            kind=CandidateKind.REVIEW,
            title="Review heaps",
            estimated_minutes=6,
            question_ids=(1, 1),
        )


def test_stable_candidate_id_is_deterministic():
    first = stable_candidate_id(
        kind=CandidateKind.PRACTICE,
        source="built-in",
        source_ids=(7,),
    )
    second = stable_candidate_id(
        kind=CandidateKind.PRACTICE,
        source="built-in",
        source_ids=(7,),
    )

    assert first == second == "practice:built-in:7"
