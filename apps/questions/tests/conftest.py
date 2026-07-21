import pytest

from apps.accounts.models import User
from apps.questions.models import BehaviouralQuestion, DebugQuestion, TechnicalQuestion


@pytest.fixture
def user(db):
    return User.objects.create_user(email="tee@example.com", password="safe-test-password")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email="other@example.com", password="safe-test-password")


@pytest.fixture
def technical_question(user):
    return TechnicalQuestion.objects.create(
        owner=user,
        title="Explain binary search on answer",
        prompt="How do you recognise and solve a binary-search-on-answer problem?",
        company="Amazon",
        difficulty="MEDIUM",
        topic="Algorithms",
        first_hint="Look for a monotonic feasibility condition.",
        pattern="Binary search on answer",
        data_structure="Array",
        intuition="Search the answer space instead of array indices.",
        brute_force="Try every candidate answer.",
        optimal_approach="Binary search the smallest feasible candidate.",
        complexity="O(n log m)",
        mistakes="Using the wrong boundary update.",
        code="while (left <= right) { /* ... */ }",
    )


@pytest.fixture
def behavioural_question(user):
    return BehaviouralQuestion.objects.create(
        owner=user,
        title="Conflict with a teammate",
        prompt="Tell me about a time you disagreed with a teammate.",
        company="Amazon",
        star_answer="Situation, task, action and result.",
        leadership_principles="Earn Trust\nHave Backbone",
        stories="Capstone project disagreement.",
        follow_ups="What would you do differently?",
    )


@pytest.fixture
def debug_question(user):
    return DebugQuestion.objects.create(
        owner=user,
        title="Missing response field",
        prompt="A repository test expects an assignee field but the API omits it.",
        repository="Spring repository task",
        bug_type=DebugQuestion.BugType.MISSING_FIELD,
        broken_code='return Map.of("status", status);',
        fix="Add the required assignee field and a safe default.",
        tests='assertThat(response.get("assignee")).isNotNull();',
    )
