from __future__ import annotations

import re
from dataclasses import dataclass
from textwrap import dedent


HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True, slots=True)
class MarkdownChunk:
    position: int
    heading: str
    content: str
    character_count: int
    token_estimate: int


def normalise_markdown(value):
    value = dedent(value)

    lines = [
        line.rstrip()
        for line in value.replace("\r\n", "\n").split("\n")
    ]
    normalised = "\n".join(lines).strip()

    return re.sub(r"\n{3,}", "\n\n", normalised)


def _token_estimate(value):
    # A deliberately conservative approximation for ingestion metadata.
    return max(1, (len(value) + 3) // 4)


def _heading_label(heading_stack):
    return " › ".join(
        heading
        for heading in heading_stack
        if heading
    )


def _split_long_text(value, max_characters):
    words = value.split()
    if not words:
        return []

    parts = []
    current_words = []
    current_length = 0

    for word in words:
        added_length = len(word) + (1 if current_words else 0)

        if (
            current_words
            and current_length + added_length > max_characters
        ):
            parts.append(" ".join(current_words))
            current_words = [word]
            current_length = len(word)
            continue

        current_words.append(word)
        current_length += added_length

    if current_words:
        parts.append(" ".join(current_words))

    return parts


def _paragraphs_with_headings(markdown):
    heading_stack = []
    current_lines = []

    def flush():
        if not current_lines:
            return None

        value = "\n".join(current_lines).strip()
        current_lines.clear()

        if not value:
            return None

        return _heading_label(heading_stack), value

    for line in markdown.splitlines():
        heading_match = HEADING_PATTERN.match(line)

        if heading_match:
            paragraph = flush()

            if paragraph is not None:
                yield paragraph

            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()

            heading_stack[:] = heading_stack[: level - 1]

            while len(heading_stack) < level - 1:
                heading_stack.append("")

            heading_stack.append(title)
            continue

        if line.strip():
            current_lines.append(line.strip())
            continue

        paragraph = flush()

        if paragraph is not None:
            yield paragraph

    paragraph = flush()

    if paragraph is not None:
        yield paragraph


def _overlap_tail(value, overlap_characters):
    if overlap_characters <= 0:
        return ""

    if len(value) <= overlap_characters:
        return value

    tail = value[-overlap_characters:]
    first_space = tail.find(" ")

    if first_space >= 0:
        tail = tail[first_space + 1 :]

    return tail.strip()


def chunk_markdown(
    markdown,
    *,
    max_characters=2400,
    overlap_characters=300,
):
    if max_characters < 200:
        raise ValueError(
            "max_characters must be at least 200."
        )

    if overlap_characters < 0:
        raise ValueError(
            "overlap_characters cannot be negative."
        )

    if overlap_characters >= max_characters:
        raise ValueError(
            "overlap_characters must be smaller than max_characters."
        )

    normalised = normalise_markdown(markdown)

    if not normalised:
        return ()

    prepared_paragraphs = []

    for heading, paragraph in _paragraphs_with_headings(
        normalised
    ):
        if len(paragraph) <= max_characters:
            prepared_paragraphs.append(
                (heading, paragraph)
            )
            continue

        prepared_paragraphs.extend(
            (heading, part)
            for part in _split_long_text(
                paragraph,
                max_characters,
            )
        )

    chunks = []
    current_heading = ""
    current_parts = []

    def flush():
        nonlocal current_parts

        if not current_parts:
            return

        content = "\n\n".join(current_parts).strip()

        if not content:
            current_parts = []
            return

        chunks.append(
            MarkdownChunk(
                position=len(chunks) + 1,
                heading=current_heading,
                content=content,
                character_count=len(content),
                token_estimate=_token_estimate(content),
            )
        )

        overlap = _overlap_tail(
            content,
            overlap_characters,
        )
        current_parts = [overlap] if overlap else []

    for heading, paragraph in prepared_paragraphs:
        proposed_parts = [
            *current_parts,
            paragraph,
        ]
        proposed = "\n\n".join(
            proposed_parts
        ).strip()

        heading_changed = (
            bool(current_parts)
            and bool(current_heading)
            and heading != current_heading
        )

        too_large = (
            bool(current_parts)
            and len(proposed) > max_characters
        )

        if heading_changed or too_large:
            flush()

        current_heading = heading

        proposed_parts = [
            *current_parts,
            paragraph,
        ]
        proposed = "\n\n".join(
            proposed_parts
        ).strip()

        if (
            len(proposed) > max_characters
            and current_parts
        ):
            current_parts = []

        current_parts.append(paragraph)

    flush()

    return tuple(chunks)
