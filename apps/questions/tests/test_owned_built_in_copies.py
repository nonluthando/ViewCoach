import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.questions.models import Question, TechnicalQuestion, UserQuestionState

pytestmark = pytest.mark.django_db


def test_saving_built_in_creates_complete_owned_copy(client, user):
    call_command("seed_question_bank")
    source = TechnicalQuestion.objects.get(system_key="technical-two-sum")
    client.force_login(user)

    response = client.post(
        reverse("questions:toggle_bookmark", args=[source.pk])
    )

    copied = TechnicalQuestion.objects.get(
        owner=user,
        source_system_question=source,
    )
    assert response.status_code == 302
    assert response.url == reverse("questions:detail", args=[copied.pk])
    assert copied.is_system is False
    assert copied.system_key is None
    assert copied.title == source.title
    assert copied.prompt == source.prompt
    assert copied.intuition == source.intuition
    assert copied.optimal_approach == source.optimal_approach
    assert copied.code == source.code


def test_saving_same_built_in_twice_does_not_duplicate(client, user):
    call_command("seed_question_bank")
    source = Question.objects.get(system_key="technical-two-sum")
    client.force_login(user)
    url = reverse("questions:toggle_bookmark", args=[source.pk])

    client.post(url)
    client.post(url)

    assert (
        Question.objects.filter(
            owner=user,
            source_system_question=source,
        ).count()
        == 1
    )
    assert UserQuestionState.objects.get(
        user=user,
        question=source,
    ).bookmarked is True


def test_bulk_save_increases_dashboard_count(client, user):
    call_command("seed_question_bank")
    sources = list(
        Question.objects.filter(is_system=True).order_by("pk")[:3]
    )
    client.force_login(user)

    before = client.get(reverse("dashboard"))
    assert before.context["question_count"] == 0

    client.post(
        reverse("questions:bulk_save_built_in"),
        {
            "selected_built_in_questions": [
                question.pk for question in sources
            ]
        },
    )

    after = client.get(reverse("dashboard"))
    assert after.context["question_count"] == 3
    assert (
        Question.objects.filter(
            owner=user,
            source_system_question__in=sources,
        ).count()
        == 3
    )


def test_convert_saved_built_ins_creates_owned_copy(user):
    call_command("seed_question_bank")
    source = Question.objects.get(system_key="technical-two-sum")
    UserQuestionState.objects.create(
        user=user,
        question=source,
        bookmarked=True,
    )

    call_command("convert_saved_built_ins")

    assert Question.objects.filter(
        owner=user,
        source_system_question=source,
    ).exists()
