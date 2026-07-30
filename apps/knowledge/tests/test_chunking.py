import pytest

from apps.knowledge.chunking import chunk_markdown


def test_chunking_preserves_heading_context():
    markdown = """
    # Planner

    The planner creates a daily study plan.

    ## Review

    Due questions are handled first.

    ## Learn

    Roadmap topics use focused learning blocks.
    """

    chunks = chunk_markdown(
        markdown,
        max_characters=200,
        overlap_characters=20,
    )

    assert len(chunks) >= 3
    assert chunks[0].heading == "Planner"
    assert any(
        chunk.heading == "Planner › Review"
        for chunk in chunks
    )
    assert any(
        chunk.heading == "Planner › Learn"
        for chunk in chunks
    )


def test_chunking_splits_long_paragraphs_within_limit():
    markdown = "# Guide\n\n" + "word " * 300

    chunks = chunk_markdown(
        markdown,
        max_characters=240,
        overlap_characters=20,
    )

    assert len(chunks) > 1
    assert all(
        chunk.character_count <= 260
        for chunk in chunks
    )


def test_chunking_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_markdown(
            "Useful content.",
            max_characters=200,
            overlap_characters=200,
        )
