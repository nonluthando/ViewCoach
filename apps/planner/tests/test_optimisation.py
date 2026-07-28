import pytest

from apps.planner.candidates import CandidateKind, PlanCandidate
from apps.planner.optimisation import optimise_candidates
from apps.planner.policies import plan_policy_for_budget


pytest.importorskip("ortools")


def _roadmap_candidate(index):
    return PlanCandidate(
        candidate_id=f"roadmap:{index}",
        kind=CandidateKind.ROADMAP,
        title=f"Roadmap {index}",
        estimated_minutes=45,
        roadmap_id=index,
        topic_ids=(index,),
    )


def test_cp_sat_respects_time_and_roadmap_constraints():
    policy = plan_policy_for_budget(
        time_budget_minutes=180,
        due_count=0,
    )
    candidates = [_roadmap_candidate(index) for index in range(1, 5)]

    result = optimise_candidates(
        candidates=candidates,
        policy=policy,
        time_limit_seconds=1,
    )

    assert result.status in {"OPTIMAL", "FEASIBLE"}
    assert result.used_minutes <= 180
    assert len(
        {
            item.candidate.roadmap_id
            for item in result.selected
        }
    ) <= policy.max_roadmaps


def test_cp_sat_prevents_duplicate_question_selection():
    policy = plan_policy_for_budget(
        time_budget_minutes=60,
        due_count=2,
    )
    candidates = [
        PlanCandidate(
            candidate_id="review:first",
            kind=CandidateKind.REVIEW,
            title="Review one",
            estimated_minutes=3,
            question_ids=(1,),
        ),
        PlanCandidate(
            candidate_id="review:second",
            kind=CandidateKind.REVIEW,
            title="Review duplicate",
            estimated_minutes=3,
            question_ids=(1,),
        ),
    ]

    result = optimise_candidates(
        candidates=candidates,
        policy=policy,
        time_limit_seconds=1,
    )

    assert len(result.selected) == 1
