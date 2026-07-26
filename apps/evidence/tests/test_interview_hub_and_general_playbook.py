import pytest
from django.urls import reverse

from apps.evidence.ai_prep import AI_ASSISTED_INTERVIEW_QUESTIONS
from apps.evidence.models import (
    AIPrepAnswer,
    AIRepositoryPracticeAttempt,
    BehaviouralStory,
    EvidenceItem,
    ProjectExplanation,
)
from apps.goals.models import InterviewGoal

pytestmark = pytest.mark.django_db


def test_interview_hub_requires_authentication(client):
    response = client.get(reverse("evidence:interview_pack"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


def test_interview_hub_exposes_preparation_areas_and_progress(client, user):
    project = EvidenceItem.objects.create(
        owner=user,
        source_type=EvidenceItem.SourceType.PROJECT,
        title="ViewCoach",
    )
    ProjectExplanation.objects.create(
        evidence=project,
        quick_pitch="An adaptive interview preparation platform.",
    )
    BehaviouralStory.objects.create(
        evidence=project,
        title="Recovered a failing release",
        situation="A deployment failed.",
        actions="Traced the failure and fixed the underlying configuration.",
    )
    AIPrepAnswer.objects.create(
        user=user,
        question_key=AI_ASSISTED_INTERVIEW_QUESTIONS[0].key,
        answer_notes="I use focused prompts and verify the final diff.",
    )
    AIRepositoryPracticeAttempt.objects.create(
        user=user,
        title="Repository practice",
        feature_completed=True,
        full_suite_passed=True,
    )
    InterviewGoal.objects.create(
        user=user,
        title="Storyteller developer role",
        goal_type=InterviewGoal.GoalType.SPECIFIC_OPPORTUNITY,
        role_title="Developer",
        company="Storyteller",
        is_primary=True,
    )
    client.force_login(user)

    response = client.get(reverse("evidence:interview_pack"))
    html = response.content.decode()

    assert response.status_code == 200
    assert "Interview Hub" in html
    assert "Project explanations" in html
    assert "AI-assisted coding prep" in html
    assert "AI repository playbook" in html
    assert "General interview playbook" in html
    assert "1 of 1 projects started" in html
    assert "1 stories captured" in html
    assert "1 of 3 verified practices" in html
    assert "Storyteller developer role" in html


def test_project_explanations_remain_available_from_hub(client, user):
    EvidenceItem.objects.create(
        owner=user,
        source_type=EvidenceItem.SourceType.PROJECT,
        title="ScoreRent",
    )
    client.force_login(user)

    response = client.get(reverse("evidence:project_explanations"))

    assert response.status_code == 200
    assert "ScoreRent" in response.content.decode()


def test_general_playbook_uses_progressive_disclosure(client, user):
    client.force_login(user)

    response = client.get(reverse("evidence:general_interview_playbook"))
    html = response.content.decode()

    assert response.status_code == 200
    assert "When to ask clarifying questions" in html
    assert "What to do when you get stuck" in html
    assert "Choose the stage you need" in html
    assert 'class="interview-playbook-stage"' in html
    assert html.count("<details") >= 20
