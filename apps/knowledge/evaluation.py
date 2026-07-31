from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationCase:
    name: str
    question: str
    expected_document_slugs: tuple[str, ...]


RETRIEVAL_EVALUATION_CASES = (
    RetrievalEvaluationCase(
        name="planner-selection",
        question="Why did the planner choose this task?",
        expected_document_slugs=("planner",),
    ),
    RetrievalEvaluationCase(
        name="readiness",
        question="How does ViewCoach calculate readiness?",
        expected_document_slugs=("goals-and-readiness",),
    ),
    RetrievalEvaluationCase(
        name="mock-interviews",
        question="How do mock interview sessions work?",
        expected_document_slugs=("mock-interviews",),
    ),
    RetrievalEvaluationCase(
        name="personal-evidence",
        question="What is personal evidence used for?",
        expected_document_slugs=("personal-evidence",),
    ),
    RetrievalEvaluationCase(
        name="star-answer",
        question="How should I structure a STAR answer?",
        expected_document_slugs=("star-method",),
    ),
    RetrievalEvaluationCase(
        name="technical-screen",
        question="What happens during a technical screening call?",
        expected_document_slugs=("technical-screening",),
    ),
    RetrievalEvaluationCase(
        name="project-explanation",
        question="How should I explain a project in an interview?",
        expected_document_slugs=("project-explanations",),
    ),
)


def score_retrieval_case(case, results):
    retrieved_slugs = tuple(
        result.document_slug
        for result in results
    )
    matched = any(
        expected_slug in retrieved_slugs
        for expected_slug in case.expected_document_slugs
    )
    return matched, retrieved_slugs
