import pytest

from apps.knowledge.answering import (
    AnswerGenerationError,
    REFUSAL_ANSWER,
    answer_question,
)
from apps.knowledge.models import KnowledgeQueryLog
from apps.knowledge.retrieval import RetrievedKnowledge


class FakeGenerator:
    model = "fake-gemini-model"

    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def generate(self, *, question, context):
        self.calls.append((question, context))
        return self.answer


def result(
    *,
    chunk_id=1,
    slug="planner",
    similarity=0.82,
):
    return RetrievedKnowledge(
        chunk_id=chunk_id,
        document_slug=slug,
        document_title="Planner",
        category="PRODUCT",
        heading="Planner selection",
        content="The planner prioritises due review work.",
        source_path="knowledge_docs/product/planner.md",
        similarity=similarity,
    )


@pytest.mark.django_db
def test_answer_is_logged_with_deterministic_source():
    generator = FakeGenerator(
        "Due review work is prioritised first. [Source 1]"
    )

    grounded = answer_question(
        question="Why was this task selected?",
        retriever=lambda **kwargs: (result(),),
        generator=generator,
    )

    assert grounded.supported is True
    assert grounded.sources[0].document_slug == "planner"
    log = KnowledgeQueryLog.objects.get(pk=grounded.log_id)
    assert log.status == KnowledgeQueryLog.Status.ANSWERED
    assert log.retrieved_chunk_ids == [1]
    assert log.citations[0]["number"] == 1


@pytest.mark.django_db
def test_no_retrieval_results_returns_refusal():
    grounded = answer_question(
        question="Something undocumented",
        retriever=lambda **kwargs: (),
        generator=FakeGenerator("This must not be called."),
    )

    assert grounded.supported is False
    assert grounded.answer == REFUSAL_ANSWER
    assert KnowledgeQueryLog.objects.get().status == (
        KnowledgeQueryLog.Status.NO_EVIDENCE
    )


@pytest.mark.django_db
def test_model_can_refuse_when_context_is_insufficient():
    grounded = answer_question(
        question="Can ViewCoach book an interview?",
        retriever=lambda **kwargs: (result(),),
        generator=FakeGenerator("NOT_SUPPORTED"),
    )

    assert grounded.supported is False
    assert grounded.sources == ()


@pytest.mark.django_db
def test_invalid_model_citation_fails_closed_and_logs_error():
    with pytest.raises(AnswerGenerationError):
        answer_question(
            question="Why was this selected?",
            retriever=lambda **kwargs: (result(),),
            generator=FakeGenerator(
                "This cites a missing source. [Source 9]"
            ),
        )

    log = KnowledgeQueryLog.objects.get()
    assert log.status == KnowledgeQueryLog.Status.ERROR
    assert "not supplied" in log.error_message
