import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.evidence.models import BehaviouralStory, EvidenceItem
from apps.planner.candidate_builders import build_plan_candidates
from apps.planner.candidates import CandidateKind
from apps.planner.models import StudyRecommendation
from apps.planner.policies import plan_policy_for_budget
from apps.planner.services import generate_daily_plan
from apps.questions.models import Question, TechnicalQuestion

pytestmark = pytest.mark.django_db


def test_daily_plan_contains_required_star_task(user):
    plan = generate_daily_plan(user=user, time_budget_minutes=60)

    star = plan.recommendations.get(kind=StudyRecommendation.Kind.STAR)

    assert star.is_required is True
    assert star.action_path == reverse("evidence:create")


def test_short_plan_keeps_star_and_due_review(user):
    TechnicalQuestion.objects.create(
        owner=user,
        title="Explain queues",
        prompt="Explain queue behaviour.",
        status=Question.Status.READY_FOR_REVIEW,
        topic="Queues",
        intuition="FIFO",
    )

    plan = generate_daily_plan(user=user, time_budget_minutes=20)
    kinds = set(plan.recommendations.values_list("kind", flat=True))

    assert StudyRecommendation.Kind.STAR in kinds
    assert StudyRecommendation.Kind.REVIEW in kinds


def test_incomplete_story_becomes_daily_star_task(user):
    evidence = EvidenceItem.objects.create(
        owner=user,
        source_type=EvidenceItem.SourceType.PROJECT,
        title="ScoreRent",
        summary="Rental decision-support project.",
    )
    story = BehaviouralStory.objects.create(
        evidence=evidence,
        title="Resolving a scoring bug",
        situation="A scoring rule produced a surprising result.",
        actions="I traced and corrected the rule.",
    )

    plan = generate_daily_plan(user=user, time_budget_minutes=60)
    star = plan.recommendations.get(kind=StudyRecommendation.Kind.STAR)

    assert "Strengthen STAR story" in star.title
    assert star.action_path == reverse(
        "evidence:behavioural_story_edit",
        args=[story.pk],
    )


def test_interview_aim_builds_readiness_candidates(user):
    user.primary_need_type = User.NeedType.INTERVIEW_SKILLS
    user.save(update_fields=["primary_need_type"])
    now = timezone.now()

    build = build_plan_candidates(
        user=user,
        time_budget_minutes=120,
        plan_date=timezone.localdate(now),
        now=now,
    )
    kinds = {candidate.kind for candidate in build.candidates}

    assert {
        CandidateKind.STAR,
        CandidateKind.EVIDENCE,
        CandidateKind.GUIDE,
        CandidateKind.MOCK,
    }.issubset(kinds)
    assert build.policy.max_readiness_blocks == 2


def test_primary_aim_changes_daily_capacity_mix():
    learning = plan_policy_for_budget(
        time_budget_minutes=240,
        due_count=0,
        primary_need_type=User.NeedType.LEARN_ORGANISE,
    )
    retention = plan_policy_for_budget(
        time_budget_minutes=240,
        due_count=0,
        primary_need_type=User.NeedType.PRACTISE_RETAIN,
    )

    assert learning.max_roadmaps > retention.max_roadmaps
    assert retention.practice_target_minutes > learning.practice_target_minutes
