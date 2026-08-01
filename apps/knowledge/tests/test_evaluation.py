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

    matched, slugs = score_retrieval_case(
        case,
        (retrieved("roadmaps"), retrieved("planner")),
    )

    assert matched is True
    assert slugs == ("roadmaps", "planner")
