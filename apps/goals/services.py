from collections import OrderedDict
from datetime import timedelta
from math import ceil

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.interviews.models import MockInterview, MockInterviewItem
from apps.planner.models import StudySession
from apps.questions.models import Question
from apps.reviews.models import ReviewState
from apps.roadmaps.models import Roadmap, RoadmapTopic, UserRoadmap, UserTopicProgress

from .models import InterviewGoal, InterviewStage

READINESS_WEIGHTS = OrderedDict(
    [
        ("roadmap", 25),
        ("reviews", 25),
        ("library", 20),
        ("mocks", 20),
        ("consistency", 10),
    ]
)


def primary_goal_for_user(*, user):
    return (
        InterviewGoal.objects.filter(
            user=user,
            status=InterviewGoal.Status.ACTIVE,
            is_primary=True,
        )
        .prefetch_related("roadmaps", "stages")
        .first()
    )


def active_goals_for_user(*, user):
    return InterviewGoal.objects.filter(
        user=user,
        status=InterviewGoal.Status.ACTIVE,
    ).prefetch_related("roadmaps")


@transaction.atomic
def set_primary_goal(*, goal):
    if goal.status != InterviewGoal.Status.ACTIVE:
        raise ValueError("Only an active goal can be primary.")
    InterviewGoal.objects.filter(
        user=goal.user,
        is_primary=True,
    ).exclude(pk=goal.pk).update(is_primary=False)
    if not goal.is_primary:
        goal.is_primary = True
        goal.save(update_fields=["is_primary", "updated_at"])
    return goal


@transaction.atomic
def ensure_primary_goal(*, goal):
    has_primary = (
        InterviewGoal.objects.filter(
            user=goal.user,
            status=InterviewGoal.Status.ACTIVE,
            is_primary=True,
        )
        .exclude(pk=goal.pk)
        .exists()
    )
    if goal.is_primary or not has_primary:
        return set_primary_goal(goal=goal)
    return goal


@transaction.atomic
def set_goal_status(*, goal, status):
    valid_statuses = {value for value, _ in InterviewGoal.Status.choices}
    if status not in valid_statuses:
        raise ValueError("Choose a valid goal status.")

    was_primary = goal.is_primary
    goal.status = status
    if status != InterviewGoal.Status.ACTIVE:
        goal.is_primary = False
    goal.save(update_fields=["status", "is_primary", "updated_at"])

    if was_primary and not goal.is_primary:
        replacement = (
            InterviewGoal.objects.filter(
                user=goal.user,
                status=InterviewGoal.Status.ACTIVE,
            )
            .exclude(pk=goal.pk)
            .order_by("created_at", "pk")
            .first()
        )
        if replacement is not None:
            set_primary_goal(goal=replacement)
    sync_goal_roadmaps(goal=goal)
    return goal


@transaction.atomic
def set_current_stage(*, stage):
    if stage.completed_at is not None:
        raise ValueError("A completed stage cannot be current.")
    InterviewStage.objects.filter(
        goal=stage.goal,
        is_current=True,
    ).exclude(pk=stage.pk).update(is_current=False)
    if not stage.is_current:
        stage.is_current = True
        stage.save(update_fields=["is_current", "updated_at"])
    sync_goal_roadmaps(goal=stage.goal)
    return stage


@transaction.atomic
def complete_stage(*, stage, now=None):
    if stage.completed_at is None:
        stage.completed_at = now or timezone.now()
        stage.is_current = False
        stage.save(update_fields=["completed_at", "is_current", "updated_at"])

    next_stage = (
        stage.goal.stages.filter(completed_at__isnull=True)
        .order_by(
            "scheduled_for",
            "position",
            "pk",
        )
        .first()
    )
    if next_stage is not None:
        set_current_stage(stage=next_stage)
    sync_goal_roadmaps(goal=stage.goal)
    return stage


def _sync_enrolment_for_roadmap(*, user, roadmap):
    enrolment, _ = UserRoadmap.objects.get_or_create(
        user=user,
        roadmap=roadmap,
        defaults={
            "status": UserRoadmap.Status.IN_PROGRESS,
            "started_at": timezone.now(),
        },
    )
    update_fields = []
    if enrolment.status == UserRoadmap.Status.NOT_STARTED:
        enrolment.status = UserRoadmap.Status.IN_PROGRESS
        enrolment.started_at = enrolment.started_at or timezone.now()
        update_fields.extend(["status", "started_at"])

    linked_goals = list(
        InterviewGoal.objects.filter(
            user=user,
            status=InterviewGoal.Status.ACTIVE,
            roadmaps=roadmap,
        ).prefetch_related("stages")
    )
    deadlines = [
        linked_goal.next_deadline
        for linked_goal in linked_goals
        if linked_goal.next_deadline is not None
    ]
    deadline = min(deadlines) if deadlines else None
    if enrolment.target_date != deadline:
        enrolment.target_date = deadline
        update_fields.append("target_date")
    if update_fields:
        update_fields.append("updated_at")
        enrolment.save(update_fields=update_fields)
    return enrolment


def sync_user_roadmaps(*, user, roadmap_ids):
    return [
        _sync_enrolment_for_roadmap(user=user, roadmap=roadmap)
        for roadmap in Roadmap.objects.filter(
            pk__in=roadmap_ids,
            is_published=True,
        )
    ]


def sync_goal_roadmaps(*, goal):
    roadmap_ids = goal.roadmaps.values_list("pk", flat=True)
    return sync_user_roadmaps(user=goal.user, roadmap_ids=roadmap_ids)


def sync_goal_roadmap(*, goal):
    """Backward-compatible wrapper for callers written before multi-roadmap goals."""
    enrolments = sync_goal_roadmaps(goal=goal)
    return enrolments[0] if enrolments else None


def recommended_mock_focus(*, goal):
    if goal is None or goal.current_stage is None:
        return MockInterview.Focus.MIXED
    mapping = {
        InterviewStage.StageType.OA: MockInterview.Focus.TECHNICAL,
        InterviewStage.StageType.TECHNICAL: MockInterview.Focus.TECHNICAL,
        InterviewStage.StageType.BEHAVIOURAL: MockInterview.Focus.BEHAVIOURAL,
        InterviewStage.StageType.MIXED_FINAL: MockInterview.Focus.MIXED,
    }
    return mapping.get(goal.current_stage.stage_type, MockInterview.Focus.MIXED)


def _roadmap_component(*, goal):
    roadmap_ids = list(goal.roadmaps.values_list("pk", flat=True))
    roadmap_count = len(roadmap_ids)
    if not roadmap_ids:
        return {
            "score": 0,
            "label": "Roadmap coverage",
            "summary": "Link one or more roadmaps to measure curriculum coverage.",
            "complete": 0,
            "total": 0,
            "roadmap_count": 0,
        }
    total = RoadmapTopic.objects.filter(
        section__roadmap_id__in=roadmap_ids,
    ).count()
    complete = UserTopicProgress.objects.filter(
        user=goal.user,
        topic__section__roadmap_id__in=roadmap_ids,
        status=UserTopicProgress.Status.COMPLETED,
    ).count()
    score = round((complete / total) * 100) if total else 0
    roadmap_label = "roadmap" if roadmap_count == 1 else "roadmaps"
    return {
        "score": score,
        "label": "Roadmap coverage",
        "summary": (
            f"{complete} of {total} topics across {roadmap_count} linked "
            f"{roadmap_label} are complete."
        ),
        "complete": complete,
        "total": total,
        "roadmap_count": roadmap_count,
    }


def _review_component(*, goal, now):
    states = ReviewState.objects.filter(
        user=goal.user,
        question__owner=goal.user,
        question__status=Question.Status.READY_FOR_REVIEW,
    )
    total = states.count()
    due = states.filter(due_at__lte=now).count()
    if total == 0:
        score = 0
        summary = "No prepared questions are scheduled for spaced review yet."
    else:
        score = max(0, round(100 - ((due / total) * 100)))
        summary = f"{due} of {total} scheduled questions are currently overdue."
    return {
        "score": score,
        "label": "Review health",
        "summary": summary,
        "due": due,
        "total": total,
    }


def _library_component(*, goal):
    ready = Question.objects.filter(
        owner=goal.user,
        status=Question.Status.READY_FOR_REVIEW,
    )
    ready_count = ready.count()
    type_count = ready.values("question_type").distinct().count()
    score = min(100, (ready_count * 4) + (type_count * 10))
    return {
        "score": score,
        "label": "Question preparation",
        "summary": (
            f"{ready_count} prepared questions cover {type_count} interview format"
            f"{'s' if type_count != 1 else ''}."
        ),
        "ready_count": ready_count,
        "type_count": type_count,
    }


def _mock_component(*, goal, now):
    interviews = MockInterview.objects.filter(
        user=goal.user,
        status=MockInterview.Status.COMPLETED,
        completed_at__gte=now - timedelta(days=90),
    )
    goal_interviews = interviews.filter(goal=goal)
    if goal_interviews.exists():
        interviews = goal_interviews
    items = MockInterviewItem.objects.filter(
        interview__in=interviews,
        answered_at__isnull=False,
    )
    weights = {
        MockInterviewItem.Assessment.STRUGGLED: 25,
        MockInterviewItem.Assessment.PARTIAL: 60,
        MockInterviewItem.Assessment.CONFIDENT: 100,
        MockInterviewItem.Assessment.SKIPPED: 0,
    }
    assessments = list(items.values_list("assessment", flat=True))
    score = (
        round(sum(weights.get(value, 0) for value in assessments) / len(assessments))
        if assessments
        else 0
    )
    return {
        "score": score,
        "label": "Mock interview performance",
        "summary": (
            f"Based on {len(assessments)} answered mock-interview question"
            f"{'s' if len(assessments) != 1 else ''} from the last 90 days."
            if assessments
            else "Complete a mock interview to establish a performance baseline."
        ),
        "answer_count": len(assessments),
    }


def _consistency_component(*, goal, now):
    cutoff = now - timedelta(days=14)
    study_dates = (
        StudySession.objects.filter(
            plan__user=goal.user,
            ended_at__isnull=False,
            ended_at__gte=cutoff,
        )
        .values("ended_at__date")
        .annotate(total=Count("pk"))
        .count()
    )
    weekly_target_days = min(7, max(2, ceil(goal.weekly_minutes / 120)))
    fourteen_day_target = weekly_target_days * 2
    score = min(100, round((study_dates / fourteen_day_target) * 100))
    return {
        "score": score,
        "label": "Recent consistency",
        "summary": (
            f"Study sessions were completed on {study_dates} of the target "
            f"{fourteen_day_target} days in the last two weeks."
        ),
        "study_dates": study_dates,
        "target_days": fourteen_day_target,
    }


def readiness_report(*, goal, now=None):
    current_time = now or timezone.now()
    components = OrderedDict(
        [
            ("roadmap", _roadmap_component(goal=goal)),
            ("reviews", _review_component(goal=goal, now=current_time)),
            ("library", _library_component(goal=goal)),
            ("mocks", _mock_component(goal=goal, now=current_time)),
            ("consistency", _consistency_component(goal=goal, now=current_time)),
        ]
    )
    score = round(
        sum(
            component["score"] * READINESS_WEIGHTS[key] / 100
            for key, component in components.items()
        )
    )
    if score >= 80:
        label = "Ready"
    elif score >= 60:
        label = "Building confidence"
    elif score >= 40:
        label = "Developing"
    else:
        label = "Getting started"

    strong = [component for component in components.values() if component["score"] >= 70]
    needs_attention = [component for component in components.values() if component["score"] < 60]

    deadline = goal.next_deadline
    days_remaining = None
    if deadline is not None:
        days_remaining = (deadline - timezone.localdate(current_time)).days

    roadmap = components["roadmap"]
    topics_remaining = max(0, roadmap["total"] - roadmap["complete"])
    topics_per_week = None
    if days_remaining is not None and days_remaining > 0 and topics_remaining:
        weeks_remaining = max(days_remaining / 7, 1)
        topics_per_week = ceil(topics_remaining / weeks_remaining)

    return {
        "goal": goal,
        "score": score,
        "label": label,
        "components": components,
        "strong": strong,
        "needs_attention": needs_attention,
        "deadline": deadline,
        "days_remaining": days_remaining,
        "topics_remaining": topics_remaining,
        "topics_per_week": topics_per_week,
    }
