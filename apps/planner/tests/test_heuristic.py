from apps.planner.candidates import CandidateKind, PlanCandidate
from apps.planner.heuristic import select_candidates
from apps.planner.policies import plan_policy_for_budget


def _roadmap_candidate(index):
    return PlanCandidate(
        candidate_id=f"roadmap:{index}",
        kind=CandidateKind.ROADMAP,
        title=f"Roadmap {index}",
        estimated_minutes=45,
        roadmap_id=index,
        topic_ids=(index,),
    )


def test_heuristic_respects_roadmap_limit():
    policy = plan_policy_for_budget(
        time_budget_minutes=720,
        due_count=0,
    )
    candidates = [_roadmap_candidate(index) for index in range(1, 6)]

    result = select_candidates(
        candidates=candidates,
        policy=policy,
    )

    roadmap_ids = {item.candidate.roadmap_id for item in result.selected}
    assert len(roadmap_ids) == 4


def test_heuristic_does_not_select_duplicate_questions():
    policy = plan_policy_for_budget(
        time_budget_minutes=60,
        due_count=2,
    )
    candidates = [
        PlanCandidate(
            candidate_id="review:first",
            kind=CandidateKind.REVIEW,
            title="First review",
            estimated_minutes=3,
            question_ids=(1,),
        ),
        PlanCandidate(
            candidate_id="review:duplicate",
            kind=CandidateKind.REVIEW,
            title="Duplicate review",
            estimated_minutes=3,
            question_ids=(1,),
        ),
    ]

    result = select_candidates(
        candidates=candidates,
        policy=policy,
    )

    assert len(result.selected) == 1
    assert any(
        rejection.reason == "duplicates a selected question" for rejection in result.rejected
    )


def test_heuristic_respects_practice_allocation():
    policy = plan_policy_for_budget(
        time_budget_minutes=60,
        due_count=0,
    )
    candidates = [
        PlanCandidate(
            candidate_id=f"practice:{index}",
            kind=CandidateKind.PRACTICE,
            title=f"Practice {index}",
            estimated_minutes=15,
            question_ids=(index,),
        )
        for index in range(1, 4)
    ]

    result = select_candidates(
        candidates=candidates,
        policy=policy,
    )

    assert result.used_minutes == policy.practice_target_minutes
    assert len(result.selected) == 1
