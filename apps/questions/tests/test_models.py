import pytest

from apps.questions.models import BehaviouralQuestion, DebugQuestion, Question, TechnicalQuestion

pytestmark = pytest.mark.django_db


def test_technical_question_sets_type_and_resolves_specific(user):
    technical = TechnicalQuestion.objects.create(
        owner=user,
        title="Two pointers",
        prompt="Explain the pattern.",
    )

    base_question = Question.objects.get(pk=technical.pk)

    assert base_question.question_type == Question.Type.TECHNICAL
    assert base_question.specific == technical


def test_behavioural_question_sets_type(user):
    question = BehaviouralQuestion.objects.create(
        owner=user,
        title="Ownership story",
        prompt="Tell me about a time you took ownership.",
    )

    assert question.question_type == Question.Type.BEHAVIOURAL


def test_debug_question_sets_type(user):
    question = DebugQuestion.objects.create(
        owner=user,
        title="Off-by-one bug",
        prompt="Find the incorrect loop boundary.",
    )

    assert question.question_type == Question.Type.DEBUG


def test_typed_question_save_repairs_incorrect_type(technical_question):
    technical_question.question_type = Question.Type.DEBUG
    technical_question.save()

    technical_question.refresh_from_db()

    assert technical_question.question_type == Question.Type.TECHNICAL


def test_deleting_base_question_deletes_subtype(technical_question):
    question_id = technical_question.pk

    Question.objects.get(pk=question_id).delete()

    assert not Question.objects.filter(pk=question_id).exists()
    assert not TechnicalQuestion.objects.filter(pk=question_id).exists()
