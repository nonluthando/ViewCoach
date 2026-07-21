import uuid

import pytest
from django.urls import reverse

from apps.questions.models import BehaviouralQuestion, DebugQuestion, Question, TechnicalQuestion

pytestmark = pytest.mark.django_db


def test_question_library_requires_login(client):
    response = client.get(reverse("questions:list"))

    assert response.status_code == 302
    assert reverse("login") in response.url


def test_question_library_only_shows_owners_questions(
    client,
    user,
    other_user,
    technical_question,
):
    TechnicalQuestion.objects.create(
        owner=other_user,
        title="Private question",
        prompt="This belongs to someone else.",
    )
    client.force_login(user)

    response = client.get(reverse("questions:list"))

    assert response.status_code == 200
    assert "Explain binary search on answer" in response.content.decode()
    assert "Private question" not in response.content.decode()


def test_question_library_searches_subtype_fields(client, user, technical_question):
    client.force_login(user)

    matching_response = client.get(reverse("questions:list"), {"q": "monotonic"})
    missing_response = client.get(reverse("questions:list"), {"q": "database indexing"})

    assert technical_question.title in matching_response.content.decode()
    assert technical_question.title not in missing_response.content.decode()


def test_question_library_filters_by_type(
    client,
    user,
    technical_question,
    behavioural_question,
):
    client.force_login(user)

    response = client.get(
        reverse("questions:list"),
        {"type": Question.Type.BEHAVIOURAL},
    )
    content = response.content.decode()

    assert behavioural_question.title in content
    assert technical_question.title not in content


def test_user_can_create_technical_question(client, user):
    client.force_login(user)

    response = client.post(
        reverse("questions:create", args=["technical"]),
        {
            "submission_token": str(uuid.uuid4()),
            "title": "Sliding window",
            "prompt": "Find the longest valid window.",
            "company": "",
            "difficulty": "MEDIUM",
            "status": "ACTIVE",
            "topic": "Arrays",
            "first_hint": "Track a valid window.",
            "pattern": "Sliding Window",
            "data_structure": "HashMap",
            "intuition": "Move the left boundary only when invalid.",
            "brute_force": "Enumerate every substring.",
            "optimal_approach": "Maintain counts inside a moving window.",
            "complexity": "O(n)",
            "mistakes": "Moving left only once.",
            "code": "int left = 0;",
        },
    )

    created = TechnicalQuestion.objects.get(title="Sliding window")
    assert response.status_code == 302
    assert response.url == reverse("questions:detail", args=[created.pk])
    assert created.owner == user
    assert created.question_type == Question.Type.TECHNICAL



def test_repeated_create_submission_only_creates_one_question(client, user):
    client.force_login(user)
    submission_token = str(uuid.uuid4())
    payload = {
        "submission_token": submission_token,
        "title": "Two Sum",
        "prompt": "Return the indices of two numbers that add to the target.",
        "company": "",
        "difficulty": "EASY",
        "status": "ACTIVE",
        "topic": "DSA",
        "first_hint": "Track values already seen.",
        "pattern": "Hash Map",
        "data_structure": "HashMap",
        "intuition": "Store each value while looking for its complement.",
        "brute_force": "Check every pair.",
        "optimal_approach": "Use a map from value to index.",
        "complexity": "O(n)",
        "mistakes": "Using the same index twice.",
        "code": "",
    }
    url = reverse("questions:create", args=["technical"])

    first_response = client.post(url, payload)
    second_response = client.post(url, payload)

    questions = TechnicalQuestion.objects.filter(owner=user, title="Two Sum")
    assert first_response.status_code == 302
    assert second_response.status_code == 302
    assert questions.count() == 1
    assert first_response.url == reverse("questions:detail", args=[questions.get().pk])
    assert second_response.url == first_response.url

def test_user_can_create_behavioural_question(client, user):
    client.force_login(user)

    response = client.post(
        reverse("questions:create", args=["behavioural"]),
        {
            "submission_token": str(uuid.uuid4()),
            "title": "Failure story",
            "prompt": "Tell me about a failure.",
            "company": "",
            "status": "DRAFT",
            "star_answer": "My STAR answer",
            "leadership_principles": "Learn and Be Curious",
            "stories": "A project setback",
            "follow_ups": "What changed afterwards?",
        },
    )

    assert response.status_code == 302
    assert BehaviouralQuestion.objects.filter(owner=user, title="Failure story").exists()


def test_user_can_create_debug_question(client, user):
    client.force_login(user)

    response = client.post(
        reverse("questions:create", args=["debug"]),
        {
            "submission_token": str(uuid.uuid4()),
            "title": "Null handling",
            "prompt": "A test fails when the value is null.",
            "company": "",
            "difficulty": "EASY",
            "status": "ACTIVE",
            "repository": "Django API",
            "bug_type": "NULL_HANDLING",
            "broken_code": "value.lower()",
            "fix": "Guard the nullable value.",
            "tests": "assert response.status_code == 200",
        },
    )

    assert response.status_code == 302
    assert DebugQuestion.objects.filter(owner=user, title="Null handling").exists()


def test_technical_detail_contains_progressive_reveal_controls(
    client,
    user,
    technical_question,
):
    client.force_login(user)

    response = client.get(reverse("questions:detail", args=[technical_question.pk]))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Progressive reveal" in content
    assert "Reveal next step" in content
    assert technical_question.optimal_approach in content


def test_question_detail_returns_404_for_another_users_question(
    client,
    other_user,
    technical_question,
):
    client.force_login(other_user)

    response = client.get(reverse("questions:detail", args=[technical_question.pk]))

    assert response.status_code == 404


def test_user_can_edit_own_question(client, user, technical_question):
    client.force_login(user)

    response = client.post(
        reverse("questions:edit", args=[technical_question.pk]),
        {
            "title": "Updated binary search question",
            "prompt": technical_question.prompt,
            "company": technical_question.company,
            "difficulty": technical_question.difficulty,
            "status": technical_question.status,
            "topic": technical_question.topic,
            "first_hint": technical_question.first_hint,
            "pattern": technical_question.pattern,
            "data_structure": technical_question.data_structure,
            "intuition": technical_question.intuition,
            "brute_force": technical_question.brute_force,
            "optimal_approach": technical_question.optimal_approach,
            "complexity": technical_question.complexity,
            "mistakes": technical_question.mistakes,
            "code": technical_question.code,
        },
    )

    technical_question.refresh_from_db()
    assert response.status_code == 302
    assert technical_question.title == "Updated binary search question"


def test_user_cannot_edit_another_users_question(client, other_user, technical_question):
    client.force_login(other_user)

    response = client.get(reverse("questions:edit", args=[technical_question.pk]))

    assert response.status_code == 404


def test_delete_is_confirmed_with_post(client, user, technical_question):
    client.force_login(user)
    url = reverse("questions:delete", args=[technical_question.pk])

    get_response = client.get(url)
    post_response = client.post(url)

    assert get_response.status_code == 200
    assert post_response.status_code == 302
    assert post_response.url == reverse("questions:list")
    assert not Question.objects.filter(pk=technical_question.pk).exists()
