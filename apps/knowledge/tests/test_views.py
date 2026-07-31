import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.knowledge.answering import (
    GroundedAnswer,
    GroundedSource,
)
from apps.knowledge.models import KnowledgeQueryLog


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        email="help@example.com",
        password="test-password",
    )


def answer_result():
    return GroundedAnswer(
        answer="The planner prioritises due review. [Source 1]",
        sources=(
            GroundedSource(
                number=1,
                chunk_id=1,
                document_slug="planner",
                citation_label="Planner",
                excerpt="Due review work is prioritised.",
                similarity=0.88,
            ),
        ),
        supported=True,
        status=KnowledgeQueryLog.Status.ANSWERED,
        model="fake-model",
        latency_ms=10,
        log_id=1,
    )


@pytest.mark.django_db
def test_help_assistant_requires_login(client):
    response = client.get(
        reverse("knowledge:help_assistant")
    )

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_help_assistant_get_renders_form(client, user):
    client.force_login(user)

    response = client.get(
        reverse("knowledge:help_assistant")
    )

    assert response.status_code == 200
    assert b"Help Assistant" in response.content


@pytest.mark.django_db
def test_help_assistant_post_renders_grounded_answer(
    client,
    user,
    monkeypatch,
):
    client.force_login(user)
    monkeypatch.setattr(
        "apps.knowledge.views.answer_question",
        lambda **kwargs: answer_result(),
    )

    response = client.post(
        reverse("knowledge:help_assistant"),
        {"question": "Why did the planner choose this?"},
    )

    assert response.status_code == 200
    assert b"Sources verified" in response.content
    assert b"Due review work is prioritised" in response.content


@pytest.mark.django_db
def test_help_assistant_enforces_configured_rate_limit(
    client,
    user,
    settings,
    monkeypatch,
):
    client.force_login(user)
    settings.RAG_MAX_REQUESTS_PER_WINDOW = 1
    settings.RAG_RATE_LIMIT_WINDOW_SECONDS = 600
    KnowledgeQueryLog.objects.create(
        user=user,
        question="Previous question",
        answer="Previous answer",
        status=KnowledgeQueryLog.Status.ANSWERED,
    )

    called = False

    def should_not_run(**kwargs):
        nonlocal called
        called = True
        return answer_result()

    monkeypatch.setattr(
        "apps.knowledge.views.answer_question",
        should_not_run,
    )

    response = client.post(
        reverse("knowledge:help_assistant"),
        {"question": "Can I ask another question?"},
    )

    assert response.status_code == 200
    assert called is False
    assert b"temporary Help Assistant limit" in response.content
