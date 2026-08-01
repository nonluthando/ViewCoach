from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from pgvector.django import CosineDistance

from .embeddings import GeminiEmbeddingProvider
from .models import KnowledgeChunk, KnowledgeDocument


@dataclass(frozen=True, slots=True)
class RetrievedKnowledge:
    chunk_id: int
    document_slug: str
    document_title: str
    category: str
    heading: str
    content: str
    source_path: str
    similarity: float

    @property
    def citation_label(self):
        if self.heading:
            return f"{self.document_title} — {self.heading}"
        return self.document_title


def retrieve_knowledge(
    *,
    query,
    limit=None,
    minimum_similarity=None,
    embedder=None,
):
    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("A retrieval query cannot be empty.")

    result_limit = limit or settings.RAG_RETRIEVAL_LIMIT
    if result_limit < 1 or result_limit > 20:
        raise ValueError("Retrieval limit must be between 1 and 20.")

    threshold = (
        settings.RAG_MINIMUM_SIMILARITY if minimum_similarity is None else float(minimum_similarity)
    )
    provider = embedder or GeminiEmbeddingProvider()
    query_embedding = provider.embed_query(cleaned_query)

    candidate_limit = max(
        result_limit * 3,
        result_limit,
    )
    candidates = (
        KnowledgeChunk.objects.filter(
            document__status=(KnowledgeDocument.Status.PUBLISHED),
            embedding__isnull=False,
        )
        .select_related("document")
        .annotate(
            distance=CosineDistance(
                "embedding",
                query_embedding,
            )
        )
        .order_by(
            "distance",
            "document_id",
            "position",
        )[:candidate_limit]
    )

    results = []
    for chunk in candidates:
        similarity = 1.0 - float(chunk.distance)
        if similarity < threshold:
            continue
        results.append(
            RetrievedKnowledge(
                chunk_id=chunk.pk,
                document_slug=chunk.document.slug,
                document_title=chunk.document.title,
                category=chunk.document.category,
                heading=chunk.heading,
                content=chunk.content,
                source_path=(chunk.document.source_path),
                similarity=similarity,
            )
        )
        if len(results) >= result_limit:
            break
    return tuple(results)


def build_grounding_context(results):
    sections = []
    for index, result in enumerate(
        results,
        start=1,
    ):
        sections.append(
            "\n".join(
                [
                    (f"[Source {index}] {result.citation_label}"),
                    f"Path: {result.source_path}",
                    result.content,
                ]
            )
        )
    return "\n\n---\n\n".join(sections)
