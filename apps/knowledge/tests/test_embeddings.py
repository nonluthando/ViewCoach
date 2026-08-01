import math

import pytest

from apps.knowledge.embeddings import (
    _normalise_vector,
)


def test_truncated_gemini_vector_is_normalised():
    vector = _normalise_vector(
        [3.0, 4.0],
        dimensions=2,
    )

    assert vector == pytest.approx([0.6, 0.8])
    magnitude = math.sqrt(sum(value * value for value in vector))
    assert magnitude == pytest.approx(1.0)


def test_embedding_dimension_must_match():
    with pytest.raises(ValueError):
        _normalise_vector(
            [1.0],
            dimensions=2,
        )
