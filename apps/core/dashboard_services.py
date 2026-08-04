from __future__ import annotations

import calendar as calendar_module
from collections import defaultdict
from datetime import date, datetime, timedelta

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.accounts.needs import need_type_experience
from apps.evidence.models import BehaviouralStory
from apps.evidence.services import evidence_dashboard_summary
from apps.goals.models import InterviewGoal, InterviewStage
from apps.goals.services import primary_goal_for_user, readiness_report
from apps.interviews.models import MockInterview
from apps.planner.models import StudyRecommendation, StudySession
from apps.planner.services import generate_daily_plan, plan_summary
from apps.questions.models import Question, UserQuestionNote
from apps.reviews.models import ReviewAttempt, ReviewState
from apps.reviews.services import review_dashboard_summary
from apps.roadmaps.models import (
    Roadmap,
    UserRoadmap,
    UserTopicProgress,
    UserTopicResource,
)
from apps.roadmaps.services import progress_summary_for_user

DASHBOARD_ROADMAP_LIMIT = 4
DASHBOARD_PLAN_LIMIT = 5
DASHBOARD_UPCOMING_LIMIT = 3
STREAK_LOOKBACK_DAYS = 90
WEEKLY_CONSISTENCY_TARGET = 5


def greeting_for_time(value: datetime) -> str:
    hour = timezone.localtime(value).hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


def calculate_activity_streak(*, activity_dates: set[date], today: date) -> int:
    """Return a forgiving daily streak.

    A user does not lose yesterday's streak merely because they have not studied
    yet today. Once today has activity, the count starts from today.
    """

    if not activity_dates:
        return 0

    cursor = today if today in activity_dates else today - timedelta(days=1)
    streak = 0
    while cursor in activity_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _normalise_month(*, month_value: str, today: date) -> tuple[int, int]:
    if month_value:
        try:
            parsed = datetime.strptime(month_value, "%Y-%m").date()
            if 2000 <= parsed.year <= 2100:
                return parsed.year, parsed.month
        except ValueError:
            pass
    return today.year, today.month


def _month_shift(*, year: int, month: int, offset: int) -> tuple[int, int]:
    index = (year * 12) + (month - 1) + offset
    return index // 12, (index % 12) + 1


def _dashboard_plan(*, user, now):
    plan = generate_daily_plan(user=user, now=now)
    summary = plan_summary(plan=plan)
    recommendations = summary["recommendations"]
    unfinished = [item for item in recommendations if item.completed_at is None]
    total_count = summary["total_count"]
    completed_count = summary["completed_count"]
    progress_percent = round((completed_count / total_count) * 100) if total_count else 0

    items = []
    for position, recommendation in enumerate(recommendations[:DASHBOARD_PLAN_LIMIT], start=1):
        items.append(
            {
                "position": position,
                "title": recommendation.title,
                "description": recommendation.description,
                "rationale": recommendation.rationale,
                "duration": recommendation.estimated_minutes,
                "kind": recommendation.kind,
                "kind_label": recommendation.get_kind_display(),
                "is_required": recommendation.is_required,
                "is_completed": recommendation.completed_at is not None,
                "action_url": recommendation.action_url,
                "action_label": recommendation.action_label,
            }
        )

    current = unfinished[0] if unfinished else None
    focus_label = "Build today’s preparation plan"
    if current is not None:
        if current.topic_id:
            focus_label = current.topic.section.roadmap.title
        else:
            focus_label = current.title

    return {
        **summary,
        "items": items,
        "current": current,
        "progress_percent": progress_percent,
        "remaining_minutes": sum(item.estimated_minutes for item in unfinished),
        "remaining_count": len(unfinished),
        "focus_label": focus_label,
    }


def _focused_roadmaps(*, user):
    enrolments = list(
        UserRoadmap.objects.filter(
            user=user,
            roadmap__is_published=True,
        )
        .filter(
            Q(is_focused=True)
            | Q(
                roadmap__source=Roadmap.Source.YOUTUBE,
                roadmap__youtube_playlist__user=user,
                roadmap__youtube_playlist__is_favourite=True,
            )
        )
        .select_related("roadmap")
        .prefetch_related("roadmap__sections__topics")
        .order_by("roadmap__position", "roadmap__title", "pk")
        .distinct()[:DASHBOARD_ROADMAP_LIMIT]
    )
    roadmap_ids = [enrolment.roadmap_id for enrolment in enrolments]
    progress_by_roadmap = progress_summary_for_user(
        user=user,
        roadmap_ids=roadmap_ids,
    )

    rows = []
    for enrolment in enrolments:
        roadmap = enrolment.roadmap
        sections = list(roadmap.sections.all())
        total_count = sum(len(section.topics.all()) for section in sections)
        progress = progress_by_roadmap.get(roadmap.pk, {})
        completed_count = progress.get("completed_count", 0)
        in_progress_count = progress.get("in_progress_count", 0)
        percentage = round((completed_count / total_count) * 100) if total_count else 0
        rows.append(
            {
                "roadmap": roadmap,
                "enrolment": enrolment,
                "completed_count": completed_count,
                "in_progress_count": in_progress_count,
                "topic_count": total_count,
                "percentage": percentage,
                "url": _roadmap_url(roadmap),
                "accent": _roadmap_accent(roadmap),
                "icon": _roadmap_icon(roadmap),
            }
        )
    return rows


def _roadmap_url(roadmap):
    if roadmap.source == Roadmap.Source.YOUTUBE:
        return reverse("roadmaps:youtube_detail", args=[roadmap.slug])
    return reverse("roadmaps:detail", args=[roadmap.slug])


def _roadmap_accent(roadmap):
    if roadmap.source == Roadmap.Source.YOUTUBE:
        return "rose"
    if roadmap.source == Roadmap.Source.IBM:
        return "blue"
    mapping = {
        Roadmap.Kind.ROLE: "blue",
        Roadmap.Kind.SKILL: "green",
        Roadmap.Kind.PRACTICE: "lavender",
    }
    return mapping.get(roadmap.kind, "copper")


def _roadmap_icon(roadmap):
    mapping = {
        Roadmap.Kind.ROLE: "⌘",
        Roadmap.Kind.SKILL: "▥",
        Roadmap.Kind.PRACTICE: "Σ",
    }
    return mapping.get(roadmap.kind, "◇")


def _learning_journey(*, user, roadmap_row):
    if roadmap_row is None:
        return None

    roadmap = roadmap_row["roadmap"]
    sections = list(roadmap.sections.all())
    progress_rows = UserTopicProgress.objects.filter(
        user=user,
        topic__section__roadmap=roadmap,
    ).values_list("topic_id", "status")
    status_by_topic = dict(progress_rows)

    raw_sections = []
    for section in sections:
        topics = list(section.topics.all())
        total_count = len(topics)
        completed_count = sum(
            status_by_topic.get(topic.pk) == UserTopicProgress.Status.COMPLETED for topic in topics
        )
        has_learning = any(
            status_by_topic.get(topic.pk) == UserTopicProgress.Status.IN_PROGRESS
            for topic in topics
        )
        if total_count and completed_count == total_count:
            state = "completed"
        elif has_learning:
            state = "current"
        else:
            state = "pending"
        raw_sections.append(
            {
                "title": section.title,
                "description": section.description,
                "completed_count": completed_count,
                "topic_count": total_count,
                "state": state,
            }
        )

    current_index = next(
        (index for index, item in enumerate(raw_sections) if item["state"] == "current"),
        None,
    )
    if current_index is None:
        current_index = next(
            (index for index, item in enumerate(raw_sections) if item["state"] == "pending"),
            None,
        )
        if current_index is not None:
            raw_sections[current_index]["state"] = "current"

    next_assigned = False
    for index, item in enumerate(raw_sections):
        if item["state"] in {"completed", "current"}:
            continue
        if current_index is not None and index > current_index and not next_assigned:
            item["state"] = "next"
            next_assigned = True
        else:
            item["state"] = "later"

    labels = {
        "completed": "Completed",
        "current": "In progress",
        "next": "Up next",
        "later": "Later",
    }
    for item in raw_sections:
        item["state_label"] = labels[item["state"]]

    return {
        "roadmap": roadmap,
        "url": roadmap_row["url"],
        "sections": raw_sections,
        "percentage": roadmap_row["percentage"],
    }


def _activity_dates(*, user, now):
    cutoff = now - timedelta(days=STREAK_LOOKBACK_DAYS)
    values = []
    values.extend(
        UserTopicProgress.objects.filter(
            user=user,
            completed_at__gte=cutoff,
        ).values_list("completed_at", flat=True)
    )
    values.extend(
        ReviewAttempt.objects.filter(
            state__user=user,
            reviewed_at__gte=cutoff,
        ).values_list("reviewed_at", flat=True)
    )
    values.extend(
        StudyRecommendation.objects.filter(
            plan__user=user,
            completed_at__gte=cutoff,
        ).values_list("completed_at", flat=True)
    )
    values.extend(
        StudySession.objects.filter(
            plan__user=user,
            ended_at__gte=cutoff,
        ).values_list("ended_at", flat=True)
    )
    values.extend(
        MockInterview.objects.filter(
            user=user,
            completed_at__gte=cutoff,
        ).values_list("completed_at", flat=True)
    )
    return {timezone.localtime(value).date() for value in values if value is not None}


def _streak_summary(*, user, now):
    today = timezone.localdate(now)
    dates = _activity_dates(user=user, now=now)
    week_start = today - timedelta(days=today.weekday())
    week_active_days = sum(week_start <= activity_date <= today for activity_date in dates)
    return {
        "current": calculate_activity_streak(activity_dates=dates, today=today),
        "week_active_days": week_active_days,
        "weekly_target": WEEKLY_CONSISTENCY_TARGET,
        "is_on_target": week_active_days >= WEEKLY_CONSISTENCY_TARGET,
    }


def _calendar_data(*, user, month_value, now):
    today = timezone.localdate(now)
    year, month = _normalise_month(month_value=month_value, today=today)
    weeks = calendar_module.Calendar(firstweekday=0).monthdatescalendar(year, month)
    first_visible = weeks[0][0]
    last_visible = weeks[-1][-1]

    event_map = defaultdict(list)
    stages = (
        InterviewStage.objects.filter(
            goal__user=user,
            goal__status=InterviewGoal.Status.ACTIVE,
            completed_at__isnull=True,
            scheduled_for__range=(first_visible, last_visible),
        )
        .select_related("goal")
        .order_by("scheduled_for", "position", "pk")
    )
    for stage in stages:
        event_map[stage.scheduled_for].append(
            {
                "kind": "interview",
                "label": f"{stage.display_name} · {stage.goal.title}",
            }
        )

    review_dates = ReviewState.objects.filter(
        user=user,
        question__owner=user,
        question__status=Question.Status.READY_FOR_REVIEW,
        due_at__date__range=(first_visible, last_visible),
    ).values_list("due_at__date", flat=True)
    review_counts = defaultdict(int)
    for review_date in review_dates:
        review_counts[review_date] += 1
    for review_date, count in review_counts.items():
        event_map[review_date].append(
            {
                "kind": "review",
                "label": f"{count} review{'s' if count != 1 else ''} due",
            }
        )

    day_rows = []
    for week in weeks:
        row = []
        for day_value in week:
            events = event_map.get(day_value, [])
            kinds = {event["kind"] for event in events}
            row.append(
                {
                    "date": day_value,
                    "day": day_value.day,
                    "in_month": day_value.month == month,
                    "is_today": day_value == today,
                    "events": events,
                    "event_count": len(events),
                    "has_interview": "interview" in kinds,
                    "has_review": "review" in kinds,
                    "event_label": "; ".join(event["label"] for event in events),
                }
            )
        day_rows.append(row)

    previous_year, previous_month = _month_shift(year=year, month=month, offset=-1)
    next_year, next_month = _month_shift(year=year, month=month, offset=1)
    return {
        "year": year,
        "month": month,
        "month_label": date(year, month, 1).strftime("%B %Y"),
        "weeks": day_rows,
        "previous_query": f"?month={previous_year:04d}-{previous_month:02d}",
        "next_query": f"?month={next_year:04d}-{next_month:02d}",
    }


def _upcoming_items(*, user, plan, review_summary, now):
    today = timezone.localdate(now)
    items = []

    if review_summary["due_count"]:
        count = review_summary["due_count"]
        items.append(
            {
                "sort_date": today,
                "sort_priority": 0,
                "kind": "Review",
                "title": f"{count} review{'s' if count != 1 else ''} due",
                "meta": "Ready now",
                "url": reverse("reviews:queue"),
                "accent": "lavender",
            }
        )

    for stage in (
        InterviewStage.objects.filter(
            goal__user=user,
            goal__status=InterviewGoal.Status.ACTIVE,
            completed_at__isnull=True,
            scheduled_for__gte=today,
        )
        .select_related("goal")
        .order_by("scheduled_for", "position", "pk")[:DASHBOARD_UPCOMING_LIMIT]
    ):
        items.append(
            {
                "sort_date": stage.scheduled_for,
                "sort_priority": 0,
                "kind": "Interview",
                "title": stage.display_name,
                "meta": f"{stage.goal.title} · {stage.scheduled_for:%d %b}",
                "url": reverse("goals:detail", args=[stage.goal_id]),
                "accent": "rose",
            }
        )

    if plan["remaining_count"]:
        items.append(
            {
                "sort_date": today,
                "sort_priority": 1,
                "kind": "Plan",
                "title": f"{plan['remaining_count']} study blocks remaining",
                "meta": f"{plan['remaining_minutes']} min planned today",
                "url": reverse("planner:today"),
                "accent": "blue",
            }
        )

    items.sort(
        key=lambda item: (
            item["sort_date"],
            item["sort_priority"],
            item["kind"],
            item["title"],
        )
    )
    for item in items:
        item.pop("sort_date", None)
        item.pop("sort_priority", None)
    return items[:DASHBOARD_UPCOMING_LIMIT]


def _evidence_summary(*, user):
    summary = evidence_dashboard_summary(user=user)
    stories = list(
        BehaviouralStory.objects.filter(evidence__owner=user)
        .select_related("evidence")
        .order_by("-updated_at", "-pk")
    )
    ready_story_count = sum(story.is_interview_ready for story in stories)
    story_count = len(stories)
    summary.update(
        {
            "story_count": story_count,
            "ready_story_count": ready_story_count,
            "story_percentage": (
                round((ready_story_count / story_count) * 100) if story_count else 0
            ),
        }
    )
    return summary


def _resource_summary(*, user):
    question_note_filter = (
        ~Q(notes="") | ~Q(mistakes="") | ~Q(code_notes="") | ~Q(behavioural_notes="")
    )
    return {
        "topic_note_count": UserTopicProgress.objects.filter(user=user).exclude(notes="").count(),
        "question_note_count": UserQuestionNote.objects.filter(user=user)
        .filter(question_note_filter)
        .count(),
        "resource_count": UserTopicResource.objects.filter(user=user).count(),
        "question_count": Question.objects.filter(owner=user).count(),
    }


def build_dashboard_context(*, user, month_value="", now=None):
    current_time = now or timezone.now()
    questions = Question.objects.filter(owner=user)
    plan = _dashboard_plan(user=user, now=current_time)
    primary_goal = primary_goal_for_user(user=user)
    readiness = readiness_report(goal=primary_goal, now=current_time) if primary_goal else None
    review_summary = review_dashboard_summary(user=user, now=current_time)
    focused_roadmaps = _focused_roadmaps(user=user)
    journey = _learning_journey(
        user=user,
        roadmap_row=focused_roadmaps[0] if focused_roadmaps else None,
    )
    streak = _streak_summary(user=user, now=current_time)

    return {
        "greeting": greeting_for_time(current_time),
        "need_focus": need_type_experience(user.primary_need_type),
        "primary_goal": primary_goal,
        "readiness": readiness,
        "today_plan": plan,
        "focused_roadmaps": focused_roadmaps,
        "learning_journey": journey,
        "review_summary": review_summary,
        "question_count": questions.count(),
        "ready_question_count": questions.filter(status=Question.Status.READY_FOR_REVIEW).count(),
        "recent_questions": questions.select_related(
            "technicalquestion",
            "conceptquestion",
            "behaviouralquestion",
            "debugquestion",
        )[:5],
        "due_review_count": review_summary["due_count"],
        "reviewed_today_count": review_summary["reviewed_today_count"],
        "next_review_state": review_summary["next_state"],
        "review_metric_detail": f"{review_summary['reviewed_today_count']} reviewed today",
        "streak": streak,
        "streak_metric_detail": (
            f"{streak['week_active_days']}/{streak['weekly_target']} active days this week"
        ),
        "primary_goal_url": primary_goal.get_absolute_url() if primary_goal else "",
        "calendar": _calendar_data(
            user=user,
            month_value=month_value,
            now=current_time,
        ),
        "upcoming_items": _upcoming_items(
            user=user,
            plan=plan,
            review_summary=review_summary,
            now=current_time,
        ),
        "evidence_summary": _evidence_summary(user=user),
        "resource_summary": _resource_summary(user=user),
    }
