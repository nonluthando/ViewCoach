import json
from pathlib import Path

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.questions.models import (
    BehaviouralQuestion,
    ConceptQuestion,
    DebugQuestion,
    Question,
    TechnicalQuestion,
    UserQuestionNote,
    UserQuestionState,
)

pytestmark = pytest.mark.django_db


def test_seed_command_creates_full_built_in_question_bank():
    call_command("seed_question_bank")

    assert Question.objects.filter(is_system=True).count() == 100
    assert TechnicalQuestion.objects.filter(is_system=True).count() == 30
    assert ConceptQuestion.objects.filter(is_system=True).count() == 50
    assert DebugQuestion.objects.filter(is_system=True).count() == 10
    assert BehaviouralQuestion.objects.filter(is_system=True).count() == 10
    assert ConceptQuestion.objects.filter(
        is_system=True,
        category=ConceptQuestion.Category.JAVA,
    ).count() == 20
    assert ConceptQuestion.objects.filter(
        is_system=True,
        category=ConceptQuestion.Category.PYTHON,
    ).count() == 15
    assert ConceptQuestion.objects.filter(
        is_system=True,
        category=ConceptQuestion.Category.BACKEND,
    ).count() == 15


def test_seed_command_is_idempotent():
    call_command("seed_question_bank")
    call_command("seed_question_bank")

    assert Question.objects.filter(is_system=True).count() == 100


def test_built_in_question_is_visible_but_not_editable(client, user):
    call_command("seed_question_bank")
    question = Question.objects.filter(is_system=True).first()
    client.force_login(user)

    list_response = client.get(reverse("questions:list"))
    detail_response = client.get(reverse("questions:detail", args=[question.pk]))
    edit_response = client.get(reverse("questions:edit", args=[question.pk]))

    assert question.title in list_response.content.decode()
    assert detail_response.status_code == 200
    assert edit_response.status_code == 404


def test_user_can_save_private_notes_on_built_in_question(client, user):
    call_command("seed_question_bank")
    question = Question.objects.get(system_key="technical-two-sum")
    client.force_login(user)

    response = client.post(
        reverse("questions:notes", args=[question.pk]),
        {
            "notes": "Look up the complement before inserting.",
            "mistakes": "Do not use the same index twice.",
            "code_notes": "Map<Integer, Integer>",
            "behavioural_notes": "",
        },
    )

    note = UserQuestionNote.objects.get(user=user, question=question)
    state = UserQuestionState.objects.get(user=user, question=question)
    assert response.status_code == 302
    assert note.notes == "Look up the complement before inserting."
    assert state.status == UserQuestionState.Status.IN_PROGRESS


def test_seed_command_preserves_full_debugging_context():
    call_command("seed_question_bank")

    question = DebugQuestion.objects.get(
        system_key="debugging-partial-write-transaction"
    )

    assert "same database" in question.repository
    assert len(question.repository) > 160


def test_question_bank_json_has_unique_keys_and_expected_count():
    path = Path(__file__).resolve().parents[1] / "data" / "core_question_bank.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    questions = [
        *payload["technical_questions"],
        *payload["concept_questions"],
        *payload["debugging_questions"],
        *payload["behavioural_questions"],
    ]

    keys = [question["system_key"] for question in questions]
    titles = [question["title"] for question in questions]
    assert len(questions) == 100
    assert len(keys) == len(set(keys))
    assert len(titles) == len(set(titles))
