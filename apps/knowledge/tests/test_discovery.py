from apps.knowledge.discovery import FORM_SOURCES, discover_form_documents


def test_form_sources_are_all_loadable_and_produce_markdown():
    documents = discover_form_documents()

    assert len(documents) == len(FORM_SOURCES)

    seen_paths = set()
    for source_path, title, markdown in documents:
        assert source_path.startswith("generated://forms/")
        assert source_path not in seen_paths
        seen_paths.add(source_path)

        assert markdown.startswith(f"# {title}")
        assert "Found at:" in markdown


def test_discovered_document_lists_required_and_optional_fields():
    documents = dict((path, markdown) for path, _, markdown in discover_form_documents())
    markdown = documents["generated://forms/apps.evidence.forms.EvidenceItemForm"]

    assert "**Title** (required)" in markdown
    assert "**Organisation** (optional)" in markdown
    assert (
        "**Technologies and skills** (optional): "
        "Separate technologies or skills with commas." in markdown
    )
