from apps.knowledge.management.commands.ingest_knowledge import (
    _summary_from_markdown,
    _title_from_markdown,
)


def test_markdown_metadata_helpers():
    markdown = """
    # ViewCoach Planner

    The planner chooses what to study next.

    ## Review

    Reviews come first.
    """

    assert (
        _title_from_markdown(
            markdown,
            "Fallback",
        )
        == "ViewCoach Planner"
    )
    assert _summary_from_markdown(markdown) == ("The planner chooses what to study next.")
