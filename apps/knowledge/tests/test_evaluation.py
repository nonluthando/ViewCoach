from apps.knowledge.evaluation import (
    RETRIEVAL_EVALUATION_CASES,
    RetrievalEvaluationCase,
    score_retrieval_case,
)
from apps.knowledge.retrieval import RetrievedKnowledge


def retrieved(slug):
    return RetrievedKnowledge(
        chunk_id=1,
        document_slug=slug,
        document_title="Document",
        category="PRODUCT",
        heading="",
        content="Content",
        source_path="knowledge_docs/example.md",
        similarity=0.9,
    )


def test_evaluation_cases_have_unique_names():
    names = [case.name for case in RETRIEVAL_EVALUATION_CASES]

    assert len(names) == len(set(names))


def test_score_retrieval_case_detects_expected_document():
    case = RetrievalEvaluationCase(
        name="planner",
        question="How does the planner work?",
        expected_document_slugs=("planner",),
    )

    result = score_retrieval_case(
        case,
        (retrieved("roadmaps"), retrieved("planner")),
    )

    assert result.matched is True
    assert result.retrieved_slugs == ("roadmaps", "planner")
    # Expected doc is the 2nd result, so reciprocal rank is 1/2.
    assert result.reciprocal_rank == 0.5


def test_score_retrieval_case_reciprocal_rank_rewards_top_position():
    case = RetrievalEvaluationCase(
        name="planner",
        question="How does the planner work?",
        expected_document_slugs=("planner",),
    )

    first = score_retrieval_case(case, (retrieved("planner"), retrieved("roadmaps")))
    second = score_retrieval_case(case, (retrieved("roadmaps"), retrieved("planner")))

    assert first.reciprocal_rank == 1.0
    assert second.reciprocal_rank == 0.5
    assert first.reciprocal_rank > second.reciprocal_rank


def test_score_retrieval_case_no_match_has_zero_reciprocal_rank():
    case = RetrievalEvaluationCase(
        name="planner",
        question="How does the planner work?",
        expected_document_slugs=("planner",),
    )

    result = score_retrieval_case(case, (retrieved("roadmaps"),))

    assert result.matched is False
    assert result.reciprocal_rank == 0.0
