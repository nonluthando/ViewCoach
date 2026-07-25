import pytest
from django.urls import reverse

from apps.evidence.models import (
    BehaviouralStory,
    DecisionRecord,
    EvidenceItem,
    GoalEvidenceLink,
    QuestionEvidenceLink,
    TopicEvidenceLink,
    TopicEvidenceProfile,
)

pytestmark = pytest.mark.django_db


def test_evidence_list_requires_authentication(client):
    response = client.get(reverse("evidence:list"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


def test_user_can_create_an_evidence_record(client, user):
    client.force_login(user)

    response = client.post(
        reverse("evidence:create"),
        {
            "source_type": EvidenceItem.SourceType.PROJECT,
            "title": "ScoreRent",
            "organisation": "",
            "role_or_context": "Portfolio project",
            "start_date": "",
            "end_date": "",
            "summary": "Explainable rental decision support.",
            "problem": "Rental evaluation lacks transparency.",
            "personal_contribution": "Designed the scoring rules and API.",
            "technologies": "Python, FastAPI, PostgreSQL",
            "outcomes": "Deployed the project.",
            "lessons": "Rules should remain explainable.",
            "evidence_url": "",
        },
    )

    item = EvidenceItem.objects.get(owner=user)
    assert response.status_code == 302
    assert response.url == reverse("evidence:detail", args=[item.pk])


def test_user_cannot_open_someone_elses_evidence(client, user, other_evidence):
    client.force_login(user)

    response = client.get(reverse("evidence:detail", args=[other_evidence.pk]))

    assert response.status_code == 404


def test_user_can_add_a_decision_record(client, user, evidence_item):
    client.force_login(user)

    response = client.post(
        reverse("evidence:decision_add", args=[evidence_item.pk]),
        {
            "title": "Keep the planner deterministic",
            "context": "Recommendations need to be explainable.",
            "alternatives": "Generate the plan with an LLM.",
            "decision": "Use deterministic scoring rules.",
            "rationale": "The same inputs should produce the same plan.",
            "tradeoffs": "Rules need manual maintenance.",
            "outcome": "Every recommendation has a clear rationale.",
            "would_choose_again": "YES",
            "reflection": "AI can be added later without owning prioritisation.",
        },
    )

    assert response.status_code == 302
    assert DecisionRecord.objects.filter(evidence=evidence_item).count() == 1


def test_user_can_add_a_behavioural_story(client, user, evidence_item):
    client.force_login(user)

    response = client.post(
        reverse("evidence:story_add", args=[evidence_item.pk]),
        {
            "title": "Recovered from a failed integration patch",
            "situation": "A patch did not apply after the dashboard changed.",
            "task": "Integrate the milestone without losing recent work.",
            "actions": "Inspected the exact context and repaired the patch.",
            "result": "The patch applied and all tests passed.",
            "reflection": "Validate generated changes against the current branch.",
            "competencies": "Ownership, Debugging",
            "follow_up_questions": "How did you isolate the mismatch?",
        },
    )

    assert response.status_code == 302
    assert BehaviouralStory.objects.filter(evidence=evidence_item).count() == 1


def test_user_can_save_their_topic_interview_angle(client, user, topic):
    client.force_login(user)

    response = client.post(
        reverse("evidence:topic_profile_save", args=[topic.pk]),
        {
            "readiness": TopicEvidenceProfile.Readiness.PROJECT_EVIDENCE,
            "personal_angle": "Used database constraints in ViewCoach.",
            "interview_angle": "Explain defence in depth.",
            "evidence_gap": "No high-volume benchmark yet.",
            "follow_up_questions": "Why not rely on form validation?",
        },
    )

    profile = TopicEvidenceProfile.objects.get(user=user, topic=topic)
    assert response.status_code == 302
    assert profile.readiness == TopicEvidenceProfile.Readiness.PROJECT_EVIDENCE


def test_user_can_link_owned_evidence_to_a_topic(
    client,
    user,
    topic,
    evidence_item,
):
    client.force_login(user)

    response = client.post(
        reverse("evidence:topic_link", args=[topic.pk]),
        {
            "evidence": evidence_item.pk,
            "connection_note": "The project uses database constraints.",
        },
    )

    link = TopicEvidenceLink.objects.get(profile__user=user, profile__topic=topic)
    assert response.status_code == 302
    assert link.evidence == evidence_item


def test_user_cannot_link_another_users_evidence_to_a_topic(
    client,
    user,
    topic,
    other_evidence,
):
    client.force_login(user)

    response = client.post(
        reverse("evidence:topic_link", args=[topic.pk]),
        {"evidence": other_evidence.pk, "connection_note": "Private"},
    )

    assert response.status_code == 302
    assert TopicEvidenceLink.objects.count() == 0


def test_user_can_link_evidence_to_a_question(
    client,
    user,
    technical_question,
    evidence_item,
):
    client.force_login(user)

    response = client.post(
        reverse("evidence:question_link", args=[technical_question.pk]),
        {
            "evidence": evidence_item.pk,
            "answer_angle": "Use the ViewCoach ownership constraint example.",
        },
    )

    link = QuestionEvidenceLink.objects.get(user=user, question=technical_question)
    assert response.status_code == 302
    assert link.evidence == evidence_item


def test_user_can_link_evidence_to_an_interview_goal(
    client,
    user,
    goal,
    evidence_item,
):
    client.force_login(user)

    response = client.post(
        reverse("evidence:goal_link", args=[goal.pk]),
        {
            "evidence": evidence_item.pk,
            "relevance": GoalEvidenceLink.Relevance.CORE,
            "framing_notes": "Lead with backend architecture and testing.",
        },
    )

    link = GoalEvidenceLink.objects.get(user=user, goal=goal)
    assert response.status_code == 302
    assert link.relevance == GoalEvidenceLink.Relevance.CORE
