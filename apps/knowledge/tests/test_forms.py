from apps.knowledge.forms import HelpAssistantForm


def test_help_assistant_form_strips_question():
    form = HelpAssistantForm(
        {"question": "  How does the planner work?  "}
    )

    assert form.is_valid()
    assert (
        form.cleaned_data["question"]
        == "How does the planner work?"
    )


def test_help_assistant_form_rejects_tiny_question():
    form = HelpAssistantForm({"question": "why"})

    assert not form.is_valid()
