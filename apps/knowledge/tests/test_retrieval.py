import pytest

from apps.knowledge.models import (
    KnowledgeChunk,
    KnowledgeDocument,
)
from apps.knowledge.retrieval import (
    build_grounding_context,
    retrieve_knowledge,
)
from apps.knowledge.tests.fakes import FakeEmbeddingProvider


pytestmark = pytest.mark.django_db


def _vector(first, second=0.0):
    return [first, second] + [0.0] * 1534


def test_retrieval_returns_nearest_published_chunks():
    planner = KnowledgeDocument.objects.create(
        title="Planner guide",
        slug="planner-guide",
        source_path="knowledge_docs/product/planner.md",
        body_markdown="Planner documentation.",
        status=KnowledgeDocument.Status.PUBLISHED,
    )
    archived = KnowledgeDocument.objects.create(
        title="Old planner guide",
        slug="old-planner-guide",
        source_path="knowledge_docs/product/old-planner.md",
        body_markdown="Old documentation.",
        status=KnowledgeDocument.Status.ARCHIVED,
    )
    KnowledgeChunk.objects.create(
        document=planner,
        position=1,
        heading="Available time",
        content="The plan uses the time entered by the user.",
        content_checksum="a" * 64,
        character_count=45,
        token_estimate=12,
        embedding=_vector(1.0),
    )
    KnowledgeChunk.objects.create(
        document=planner,
        position=2,
        heading="Roadmaps",
        content="Roadmap blocks focus on learning.",
        content_checksum="b" * 64,
        character_count=34,
        token_estimate=9,
        embedding=_vector(0.2, 0.98),
    )
    KnowledgeChunk.objects.create(
        document=archived,
        position=1,
        heading="Archived",
        content="This must not be returned.",
        content_checksum="c" * 64,
        character_count=26,
        token_estimate=7,
        embedding=_vector(1.0),
    )
    provider = FakeEmbeddingProvider(
        vectors=[_vector(1.0)]
    )

    results = retrieve_knowledge(
        query="How does available time affect my plan?",
        limit=2,
        minimum_similarity=0.0,
        embedder=provider,
    )

    assert len(results) == 2
    assert results[0].heading == "Available time"
    assert all(
        result.document_slug != "old-planner-guide"
        for result in results
    )

    context = build_grounding_context(results)
    assert "[Source 1]" in context
    assert "knowledge_docs/product/planner.md" in context
