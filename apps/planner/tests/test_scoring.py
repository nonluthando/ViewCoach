from apps.planner.candidates import CandidateKind, PlanCandidate
from apps.planner.scoring import ranked_candidates, score_candidate


def test_overdue_review_scores_above_ordinary_roadmap_work():
    review = PlanCandidate(
        candidate_id="review:1",
        kind=CandidateKind.REVIEW,
        title="Review heaps",
        estimated_minutes=3,
        question_ids=(1,),
        is_overdue=True,
    )
    roadmap = PlanCandidate(
        candidate_id="roadmap:1",
        kind=CandidateKind.ROADMAP,
        title="Learn SQL",
        estimated_minutes=45,
        roadmap_id=1,
        topic_ids=(10,),
    )

    ranked = ranked_candidates([roadmap, review])

    assert ranked[0].candidate == review
    assert ranked[0].total_score > ranked[1].total_score


def test_goal_deadline_and_continuity_are_explainable_components():
    candidate = PlanCandidate(
        candidate_id="roadmap:deadline",
        kind=CandidateKind.ROADMAP,
        title="Learn APIs",
        estimated_minutes=45,
        roadmap_id=1,
        topic_ids=(2,),
        supports_primary_goal=True,
        continues_in_progress_work=True,
        deadline_days=3,
    )

    scored = score_candidate(candidate)
    keys = {component.key for component in scored.components}

    assert {
        "kind_base",
        "primary_goal",
        "continuity",
        "deadline_urgent",
    }.issubset(keys)
