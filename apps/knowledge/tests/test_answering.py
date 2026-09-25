import pytest

from apps.knowledge.answering import (
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


def other_result(
    *,
    chunk_id=2,
    slug="roadmaps",
    similarity=0.7,
):
    return RetrievedKnowledge(
        chunk_id=chunk_id,
        document_slug=slug,
        document_title="Roadmaps",
        category="PRODUCT",
        heading="Roadmap structure",
        content="A roadmap contains ordered topics.",
        source_path="knowledge_docs/product/roadmaps.md",
        similarity=similarity,
    )


@pytest.mark.django_db
def test_answer_is_logged_with_deterministic_source():
    generator = FakeGenerator("Due review work is prioritised first. [Source 1]")

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
    assert KnowledgeQueryLog.objects.get().status == (KnowledgeQueryLog.Status.NO_EVIDENCE)


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
def test_wholly_invalid_citation_is_treated_as_unsupported():
    # A citation number outside the supplied sources means there's nothing
    # safe to attribute the answer to. This degrades to the same refusal
    # path as NOT_SUPPORTED rather than throwing the answer away with an
    # exception — a single bad reference shouldn't turn into a 500.
    grounded = answer_question(
        question="Why was this selected?",
        retriever=lambda **kwargs: (result(),),
        generator=FakeGenerator("This cites a missing source. [Source 9]"),
    )

    assert grounded.supported is False
    assert grounded.answer == REFUSAL_ANSWER
    log = KnowledgeQueryLog.objects.get()
    assert log.status == KnowledgeQueryLog.Status.NO_EVIDENCE


@pytest.mark.django_db
def test_uncited_answer_is_treated_as_unsupported_not_fully_cited():
    # Previously, an answer with zero [Source N] references defaulted to
    # citing *every* retrieved chunk, overstating how well-grounded it was.
    grounded = answer_question(
        question="Why was this selected?",
        retriever=lambda **kwargs: (result(), other_result()),
        generator=FakeGenerator("Due review work is prioritised first."),
    )

    assert grounded.supported is False
    assert grounded.sources == ()
    log = KnowledgeQueryLog.objects.get()
    assert log.status == KnowledgeQueryLog.Status.NO_EVIDENCE


@pytest.mark.django_db
def test_partially_invalid_citations_keep_the_valid_sources():
    # A mix of a real and an out-of-range citation should keep the real
    # one rather than discarding the whole answer.
    grounded = answer_question(
        question="Why was this selected?",
        retriever=lambda **kwargs: (result(), other_result()),
        generator=FakeGenerator("Due review work is prioritised first. [Source 1] [Source 9]"),
    )

    assert grounded.supported is True
    assert [source.number for source in grounded.sources] == [1]
    log = KnowledgeQueryLog.objects.get()
    assert log.status == KnowledgeQueryLog.Status.ANSWERED
