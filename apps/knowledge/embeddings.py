from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Protocol

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from google import genai
from google.genai import types


class EmbeddingProvider(Protocol):
    model: str
    dimensions: int

    def embed_documents(
        self,
        *,
        texts,
        titles=None,
    ):
        ...

    def embed_query(self, query):
        ...


def _normalise_vector(
    values,
    *,
    dimensions,
):
    vector = [
        float(value)
        for value in values
    ]

    if len(vector) != dimensions:
        raise ValueError(
            "Embedding dimension mismatch: "
            f"expected {dimensions}, "
            f"received {len(vector)}."
        )

    if not all(
        math.isfinite(value)
        for value in vector
    ):
        raise ValueError(
            "Embedding contains a non-finite value."
        )

    magnitude = math.sqrt(
        sum(
            value * value
            for value in vector
        )
    )

    if magnitude == 0:
        raise ValueError(
            "Embedding has zero magnitude."
        )

    return [
        value / magnitude
        for value in vector
    ]


@dataclass(slots=True)
class GeminiEmbeddingProvider:
    model: str | None = None
    dimensions: int | None = None
    client: genai.Client = field(
        init=False,
        repr=False,
    )

    def __post_init__(self):
        self.model = (
            self.model
            or settings.RAG_EMBEDDING_MODEL
        )
        self.dimensions = (
            self.dimensions
            or settings.RAG_EMBEDDING_DIMENSIONS
        )

        api_key = settings.GEMINI_API_KEY

        if not api_key:
            raise ImproperlyConfigured(
                "GEMINI_API_KEY is required "
                "to create embeddings."
            )

        self.client = genai.Client(
            api_key=api_key
        )

    def _extract_embedding(
        self,
        response,
    ):
        if not response.embeddings:
            raise RuntimeError(
                "Gemini returned no embedding."
            )

        values = response.embeddings[0].values

        if values is None:
            raise RuntimeError(
                "Gemini returned an empty embedding."
            )

        return _normalise_vector(
            values,
            dimensions=self.dimensions,
        )

    def embed_documents(
        self,
        *,
        texts,
        titles=None,
    ):
        cleaned = [
            text.strip()
            for text in texts
        ]

        if (
            not cleaned
            or any(
                not text
                for text in cleaned
            )
        ):
            raise ValueError(
                "Document embedding input must "
                "contain non-empty text."
            )

        document_titles = list(
            titles
            or [None] * len(cleaned)
        )

        if (
            len(document_titles)
            != len(cleaned)
        ):
            raise ValueError(
                "Each document embedding must "
                "have a matching title."
            )

        embeddings = []

        for text, title in zip(
            cleaned,
            document_titles,
            strict=True,
        ):
            config = types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                title=title or None,
                output_dimensionality=(
                    self.dimensions
                ),
            )

            response = (
                self.client.models.embed_content(
                    model=self.model,
                    contents=text,
                    config=config,
                )
            )

            embeddings.append(
                self._extract_embedding(
                    response
                )
            )

        return embeddings

    def embed_query(
        self,
        query,
    ):
        cleaned_query = query.strip()

        if not cleaned_query:
            raise ValueError(
                "Query embedding input "
                "cannot be empty."
            )

        response = (
            self.client.models.embed_content(
                model=self.model,
                contents=cleaned_query,
                config=types.EmbedContentConfig(
                    task_type=(
                        "RETRIEVAL_QUERY"
                    ),
                    output_dimensionality=(
                        self.dimensions
                    ),
                ),
            )
        )

        return self._extract_embedding(
            response
        )
