import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.questions.models import TechnicalQuestion

pytestmark = pytest.mark.django_db


def test_dashboard_shows_question_counts_and_recent_questions(client):
    user = User.objects.create_user(email="tee@example.com", password="safe-test-password")
    question = TechnicalQuestion.objects.create(
        owner=user,
        title="Explain heaps",
        prompt="What makes a heap useful?",
    )
    client.force_login(user)

    response = client.get(reverse("dashboard"))

    assert response.status_code == 200
    assert response.context["question_count"] == 1
    assert response.context["ready_question_count"] == 0
    assert question.title in response.content.decode()
