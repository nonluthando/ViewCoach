import pytest
from django.test import override_settings

from apps.knowledge.ingestion import ingest_document, upsert_document
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
        body_markdown=("# Planner\n\n" + "The planner chooses focused work. " * 30),
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
    assert document.chunks.filter(embedding__isnull=False).count() == result.chunks_created


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


def _defaults(**overrides):
    base = {
        "title": "Project Explanations",
        "slug": "project-explanations",
        "category": KnowledgeDocument.Category.INTERVIEW_PREP,
        "summary": "How to explain a project.",
        "body_markdown": "# Project Explanations\n\nStart with the problem.",
        "status": KnowledgeDocument.Status.PUBLISHED,
        "published_at": None,
    }
    base.update(overrides)
    return base


def test_upsert_document_creates_when_nothing_matches():
    document, created = upsert_document(
        source_path="knowledge_docs/interview-prep/project-explanations.md",
        defaults=_defaults(),
    )

    assert created is True
    assert document.slug == "project-explanations"
    assert KnowledgeDocument.objects.count() == 1


def test_upsert_document_updates_matching_source_path():
    existing = KnowledgeDocument.objects.create(
        source_path="knowledge_docs/interview-prep/project-explanations.md",
        **_defaults(title="Old Title"),
    )

    document, created = upsert_document(
        source_path="knowledge_docs/interview-prep/project-explanations.md",
        defaults=_defaults(title="New Title"),
    )

    assert created is False
    assert document.pk == existing.pk
    assert document.title == "New Title"
    assert KnowledgeDocument.objects.count() == 1


def test_upsert_document_reuses_stale_row_when_source_path_moved():
    # Reproduces the production failure: a file moves from an old,
    # broken path to a corrected one. Its slug doesn't change, but a
    # plain update_or_create(source_path=...) would try to INSERT a
    # second row and crash on KnowledgeDocument.slug's unique
    # constraint, because it only matches on the (now different)
    # source_path.
    stale = KnowledgeDocument.objects.create(
        source_path="knowledge_docs/.gitkeep/interview-prep/project-explanations.md",
        **_defaults(),
    )

    document, created = upsert_document(
        source_path="knowledge_docs/interview-prep/project-explanations.md",
        defaults=_defaults(title="Project Explanations"),
    )

    assert created is False
    assert document.pk == stale.pk
    assert document.source_path == "knowledge_docs/interview-prep/project-explanations.md"
    assert KnowledgeDocument.objects.count() == 1
    assert KnowledgeDocument.objects.filter(slug="project-explanations").count() == 1
