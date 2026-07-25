import pytest

from apps.evidence.forms import (
    BehaviouralStoryForm,
    EvidenceItemForm,
    GoalEvidenceLinkForm,
    TopicEvidenceProfileForm,
)
from apps.evidence.models import EvidenceItem, TopicEvidenceProfile

pytestmark = pytest.mark.django_db


def test_evidence_item_form_accepts_a_project_case_study():
    form = EvidenceItemForm(
        data={
            "source_type": EvidenceItem.SourceType.PROJECT,
            "title": "ViewCoach",
            "organisation": "",
            "role_or_context": "Full-stack portfolio project",
            "start_date": "2026-07-01",
            "end_date": "",
            "summary": "Interview preparation platform.",
            "problem": "Preparation is fragmented.",
            "personal_contribution": "Designed and built the application.",
            "technologies": "Python, Django",
            "outcomes": "Delivered a deployed application.",
            "lessons": "Deterministic planning is explainable.",
            "evidence_url": "https://example.com/viewcoach",
        }
    )

    assert form.is_valid(), form.errors


def test_goal_link_form_only_lists_current_users_evidence(
    user,
    evidence_item,
    other_evidence,
):
    form = GoalEvidenceLinkForm(user=user)

    assert list(form.fields["evidence"].queryset) == [evidence_item]
    assert other_evidence not in form.fields["evidence"].queryset


def test_topic_profile_form_accepts_interview_framing():
    form = TopicEvidenceProfileForm(
        data={
            "readiness": TopicEvidenceProfile.Readiness.INTERVIEW_READY,
            "personal_angle": "Used constraints in ViewCoach.",
            "interview_angle": "Explain persistence-layer invariants.",
            "evidence_gap": "Limited scale testing.",
            "follow_up_questions": "How would this change at higher scale?",
        }
    )

    assert form.is_valid(), form.errors


def test_behavioural_story_requires_situation_and_actions():
    form = BehaviouralStoryForm(data={"title": "Debugged a failed patch"})

    assert not form.is_valid()
    assert "situation" in form.errors
    assert "actions" in form.errors
