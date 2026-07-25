from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.evidence.models import (
    DecisionRecord,
    GoalEvidenceLink,
    QuestionEvidenceLink,
    TopicEvidenceLink,
    TopicEvidenceProfile,
)
from apps.goals.models import InterviewGoal
from apps.questions.models import TechnicalQuestion

pytestmark = pytest.mark.django_db


def test_evidence_item_exposes_clean_technology_list(evidence_item):
    evidence_item.technologies = "Python, Django,  PostgreSQL, "

    assert evidence_item.technology_list == ["Python", "Django", "PostgreSQL"]


def test_evidence_item_rejects_end_date_before_start(evidence_item):
    evidence_item.start_date = date(2026, 7, 10)
    evidence_item.end_date = date(2026, 7, 1)

    with pytest.raises(ValidationError):
        evidence_item.full_clean()


def test_deleting_evidence_deletes_its_decisions(evidence_item):
    DecisionRecord.objects.create(
        evidence=evidence_item,
        title="Use deterministic planning",
        decision="Use scoring rules instead of an LLM.",
    )

    evidence_item.delete()

    assert DecisionRecord.objects.count() == 0


def test_only_one_topic_profile_exists_per_user_and_topic(user, topic):
    TopicEvidenceProfile.objects.create(user=user, topic=topic)

    with pytest.raises(IntegrityError):
        TopicEvidenceProfile.objects.create(user=user, topic=topic)


def test_topic_link_rejects_evidence_from_another_user(user, topic, other_evidence):
    profile = TopicEvidenceProfile.objects.create(user=user, topic=topic)
    link = TopicEvidenceLink(profile=profile, evidence=other_evidence)

    with pytest.raises(ValidationError):
        link.full_clean()


def test_question_link_accepts_a_question_owned_by_the_user(
    user,
    technical_question,
    evidence_item,
):
    link = QuestionEvidenceLink(
        user=user,
        question=technical_question,
        evidence=evidence_item,
    )

    link.full_clean()


def test_question_link_rejects_another_users_private_question(
    user,
    other_user,
    evidence_item,
):
    private_question = TechnicalQuestion.objects.create(
        owner=other_user,
        title="Private question",
        prompt="Private prompt",
    )
    link = QuestionEvidenceLink(
        user=user,
        question=private_question,
        evidence=evidence_item,
    )

    with pytest.raises(ValidationError):
        link.full_clean()


def test_goal_link_rejects_goal_owned_by_another_user(
    user,
    other_user,
    evidence_item,
):
    other_goal = InterviewGoal.objects.create(
        user=other_user,
        title="Other goal",
        goal_type=InterviewGoal.GoalType.GENERAL_PREPARATION,
        role_title="Software Engineer",
    )
    link = GoalEvidenceLink(
        user=user,
        goal=other_goal,
        evidence=evidence_item,
    )

    with pytest.raises(ValidationError):
        link.full_clean()
