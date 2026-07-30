import pytest
from django.test import override_settings

from apps.knowledge.ingestion import ingest_document
from apps.knowledge.models import KnowledgeDocument
from apps.knowledge.tests.fakes import FakeEmbeddingProvider


pytestmark = pytest.mark.django_db


@override_settings(
    RAG_CHUNK_MAX_CHARACTERS=240,
    RAG_CHUNK_OVERLAP_CHARACTERS=20,
    RAG_EMBEDDING_MODEL="fake-gemini-embedding-model",
)
def test_ingestion_replaces_chunks_and_stores_embeddings():
    document = KnowledgeDocument.objects.create(
        title="Planner guide",
        slug="planner-guide",
        source_path="knowledge_docs/product/planner.md",
        body_markdown=(
            "# Planner\n\n"
            + "The planner chooses focused work. " * 30
        ),
        status=KnowledgeDocument.Status.PUBLISHED,
    )
    provider = FakeEmbeddingProvider()

    result = ingest_document(
        document=document,
        embedder=provider,
    )

    document.refresh_from_db()
    assert result.skipped is False
    assert result.chunks_created > 1
    assert document.chunk_count == result.chunks_created
    assert document.embedding_model == provider.model
    assert document.chunks.filter(
        embedding__isnull=False
    ).count() == result.chunks_created


@override_settings(
    RAG_CHUNK_MAX_CHARACTERS=400,
    RAG_CHUNK_OVERLAP_CHARACTERS=20,
    RAG_EMBEDDING_MODEL="fake-gemini-embedding-model",
)
def test_unchanged_document_skips_reingestion():
    document = KnowledgeDocument.objects.create(
        title="Review guide",
        slug="review-guide",
        source_path="knowledge_docs/product/reviews.md",
        body_markdown="# Reviews\n\nDue questions come first.",
        status=KnowledgeDocument.Status.PUBLISHED,
    )
    provider = FakeEmbeddingProvider()
    first = ingest_document(
        document=document,
        embedder=provider,
    )
    second = ingest_document(
        document=document,
        embedder=provider,
    )

    assert first.skipped is False
    assert second.skipped is True
    assert len(provider.document_calls) == 1
