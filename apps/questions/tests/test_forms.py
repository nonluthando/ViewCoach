import pytest

from apps.questions.forms import BehaviouralQuestionForm, DebugQuestionForm, TechnicalQuestionForm

pytestmark = pytest.mark.django_db


def test_technical_form_requires_title_and_prompt():
    form = TechnicalQuestionForm(data={"status": "ACTIVE"})

    assert not form.is_valid()
    assert "title" in form.errors
    assert "prompt" in form.errors


def test_behavioural_form_does_not_ask_for_difficulty():
    form = BehaviouralQuestionForm()

    assert "difficulty" not in form.fields


def test_debug_form_accepts_known_bug_type(user):
    form = DebugQuestionForm(
        owner=user,
        data={
            "title": "Wrong default",
            "prompt": "A required value has no default.",
            "status": "ACTIVE",
            "difficulty": "MEDIUM",
            "bug_type": "INCORRECT_DEFAULT",
        },
    )

    assert form.is_valid(), form.errors
