import pytest

from apps.accounts.models import User
from apps.questions.models import Question, TechnicalQuestion


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="tee@example.com",
        password="safe-test-password",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="other@example.com",
        password="safe-test-password",
    )


@pytest.fixture
def technical_question(user):
    return TechnicalQuestion.objects.create(
        owner=user,
        title="Explain heaps",
        prompt="Explain how a min heap works and when you would use one.",
        difficulty=Question.Difficulty.MEDIUM,
        status=Question.Status.READY_FOR_REVIEW,
        topic="Heaps",
        intuition="The smallest value stays at the root.",
        optimal_approach="Use a priority queue for repeated minimum access.",
    )
