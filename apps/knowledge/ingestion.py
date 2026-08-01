from __future__ import annotations

import hashlib
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .chunking import chunk_markdown, normalise_markdown
from .embeddings import GeminiEmbeddingProvider
from .models import KnowledgeChunk, KnowledgeDocument


@dataclass(frozen=True, slots=True)
class IngestionResult:
    document_id: int
    chunks_created: int
    skipped: bool
    embedded: bool


def _checksum(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _embedding_text(*, document, chunk):
    parts = [document.title]
    if document.summary:
        parts.append(document.summary)
    if chunk.heading:
        parts.append(chunk.heading)
    parts.append(chunk.content)
    return "\n\n".join(parts)


def _embedding_title(*, document, chunk):
    if chunk.heading:
        return f"{document.title} — {chunk.heading}"
    return document.title


def ingest_document(
    *,
    document,
    embedder=None,
    force=False,
    create_embeddings=True,
    now=None,
):
    body = normalise_markdown(document.body_markdown)
    if not body:
        raise ValueError("Knowledge documents must contain non-empty Markdown.")

    content_checksum = _checksum(body)
    expected_model = (
        getattr(embedder, "model", "") if embedder is not None else settings.RAG_EMBEDDING_MODEL
    )
    existing_chunks = document.chunks.count()
    already_current = (
        not force
        and document.content_checksum == content_checksum
        and existing_chunks == document.chunk_count
        and existing_chunks > 0
        and (not create_embeddings or document.embedding_model == expected_model)
    )
    if already_current:
        return IngestionResult(
            document_id=document.pk,
            chunks_created=existing_chunks,
            skipped=True,
            embedded=create_embeddings,
        )

    chunk_specs = chunk_markdown(
        body,
        max_characters=settings.RAG_CHUNK_MAX_CHARACTERS,
        overlap_characters=(settings.RAG_CHUNK_OVERLAP_CHARACTERS),
    )
    if not chunk_specs:
        raise ValueError("The document did not produce any searchable chunks.")

    embeddings = [None] * len(chunk_specs)
    embedding_model = ""
    if create_embeddings:
        provider = embedder or GeminiEmbeddingProvider()
        embedding_inputs = [
            _embedding_text(
                document=document,
                chunk=chunk,
            )
            for chunk in chunk_specs
        ]
        embedding_titles = [
            _embedding_title(
                document=document,
                chunk=chunk,
            )
            for chunk in chunk_specs
        ]
        embeddings = provider.embed_documents(
            texts=embedding_inputs,
            titles=embedding_titles,
        )
        if len(embeddings) != len(chunk_specs):
            raise RuntimeError("The embedding provider returned the wrong result count.")
        embedding_model = provider.model

    current_time = now or timezone.now()
    chunk_objects = [
        KnowledgeChunk(
            document=document,
            position=chunk.position,
            heading=chunk.heading,
            content=chunk.content,
            content_checksum=_checksum(chunk.content),
            character_count=chunk.character_count,
            token_estimate=chunk.token_estimate,
            embedding=embedding,
        )
        for chunk, embedding in zip(
            chunk_specs,
            embeddings,
            strict=True,
        )
    ]

    with transaction.atomic():
        locked_document = KnowledgeDocument.objects.select_for_update().get(pk=document.pk)
        locked_document.chunks.all().delete()
        KnowledgeChunk.objects.bulk_create(chunk_objects)

        locked_document.body_markdown = body
        locked_document.content_checksum = content_checksum
        locked_document.embedding_model = embedding_model
        locked_document.chunk_count = len(chunk_objects)
        locked_document.last_ingested_at = current_time
        locked_document.save(
            update_fields=[
                "body_markdown",
                "content_checksum",
                "embedding_model",
                "chunk_count",
                "last_ingested_at",
                "updated_at",
            ]
        )

    document.refresh_from_db()
    return IngestionResult(
        document_id=document.pk,
        chunks_created=len(chunk_objects),
        skipped=False,
        embedded=create_embeddings,
    )
