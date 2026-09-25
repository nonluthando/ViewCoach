from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationCase:
    name: str
    question: str
    expected_document_slugs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RetrievalCaseResult:
    matched: bool
    retrieved_slugs: tuple[str, ...]
    reciprocal_rank: float


RETRIEVAL_EVALUATION_CASES = (
    # --- PRODUCT ---
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
        name="roadmaps",
        question="What is the difference between a roadmap topic and a review question?",
        expected_document_slugs=("roadmaps",),
    ),
    RetrievalEvaluationCase(
        name="questions-and-reviews",
        question="When does a question become eligible for spaced review?",
        expected_document_slugs=("questions-and-reviews",),
    ),
    # --- INTERVIEW_PREP ---
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
    RetrievalEvaluationCase(
        name="screening-interviews",
        question="How long does a recruiter screening call typically last?",
        expected_document_slugs=("screening-interviews",),
    ),
    # --- SYSTEM: hand-written ---
    RetrievalEvaluationCase(
        name="navigation",
        question="Where do I find the Evidence Bag in ViewCoach?",
        expected_document_slugs=("navigation",),
    ),
    RetrievalEvaluationCase(
        name="help-assistant-scope",
        question="Can the Help Assistant see my private evidence and interview history?",
        expected_document_slugs=("help-assistant",),
    ),
    # --- SYSTEM: generated from forms ---
    RetrievalEvaluationCase(
        name="log-evidence-fields",
        question="What fields do I fill in when logging a new piece of evidence?",
        expected_document_slugs=("logging-evidence-in-the-evidence-bag",),
    ),
    RetrievalEvaluationCase(
        name="project-explanation-form",
        question="What does the project explanation form ask for?",
        expected_document_slugs=("explaining-a-project-in-the-evidence-bag",),
    ),
    RetrievalEvaluationCase(
        name="behavioural-story-fields",
        question="What fields make up a behavioural STAR story in ViewCoach?",
        expected_document_slugs=("writing-a-behavioural-star-story",),
    ),
    RetrievalEvaluationCase(
        name="interview-goal-weekly-minutes",
        question="How do I set weekly study time on an interview goal?",
        expected_document_slugs=("setting-an-interview-goal",),
    ),
    RetrievalEvaluationCase(
        name="daily-plan-hours",
        question="How many hours can I enter when generating today's plan?",
        expected_document_slugs=("generating-todays-plan",),
    ),
    RetrievalEvaluationCase(
        name="start-mock-interview-options",
        question="What options do I choose when starting a mock interview?",
        expected_document_slugs=("starting-a-mock-interview",),
    ),
    RetrievalEvaluationCase(
        name="mock-interview-self-assessment",
        question="How do I self-assess my answer during a mock interview?",
        expected_document_slugs=("answering-during-a-mock-interview",),
    ),
    RetrievalEvaluationCase(
        name="question-notes-fields",
        question="What kind of notes can I add to a review question?",
        expected_document_slugs=("adding-notes-to-a-review-question",),
    ),
    RetrievalEvaluationCase(
        name="preparation-preferences",
        question="How do I set my primary and secondary preparation aims?",
        expected_document_slugs=("setting-preparation-preferences",),
    ),
)


def score_retrieval_case(case, results) -> RetrievalCaseResult:
    retrieved_slugs = tuple(result.document_slug for result in results)
    reciprocal_rank = 0.0
    for position, slug in enumerate(retrieved_slugs, start=1):
        if slug in case.expected_document_slugs:
            reciprocal_rank = 1 / position
            break
    return RetrievalCaseResult(
        matched=reciprocal_rank > 0,
        retrieved_slugs=retrieved_slugs,
        reciprocal_rank=reciprocal_rank,
    )
