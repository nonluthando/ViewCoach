from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.dashboard_services import (
    _calendar_data,
    _dashboard_plan,
    _focused_roadmaps,
    _learning_journey,
    _upcoming_items,
    calculate_activity_streak,
    greeting_for_time,
)
from apps.goals.models import InterviewGoal, InterviewStage
from apps.roadmaps.models import (
    Roadmap,
    RoadmapSection,
    RoadmapTopic,
    UserRoadmap,
    UserTopicProgress,
    YouTubePlaylistRoadmap,
)

pytestmark = pytest.mark.django_db


def _aware(year, month, day, hour=12):
    return timezone.make_aware(datetime(year, month, day, hour))


@pytest.mark.parametrize(
    ("hour", "expected"),
    [(8, "Good morning"), (13, "Good afternoon"), (19, "Good evening")],
)
def test_greeting_uses_local_time(hour, expected):
    assert greeting_for_time(_aware(2026, 8, 4, hour)) == expected


def test_activity_streak_keeps_yesterdays_streak_until_today_is_used():
    today = date(2026, 8, 4)
    dates = {today - timedelta(days=offset) for offset in (1, 2, 3)}

    assert calculate_activity_streak(activity_dates=dates, today=today) == 3

    dates.add(today)
    assert calculate_activity_streak(activity_dates=dates, today=today) == 4


def test_dashboard_plan_uses_real_completion_and_remaining_time(monkeypatch):
    completed = SimpleNamespace(
        title="Completed review",
        description="",
        rationale="",
        estimated_minutes=20,
        kind="REVIEW",
        is_required=True,
        completed_at=timezone.now(),
        topic_id=None,
        action_url="/reviews/",
        action_label="Start reviews",
        get_kind_display=lambda: "Due review",
    )
    remaining = SimpleNamespace(
        title="Continue PostgreSQL",
        description="",
        rationale="Next focused topic",
        estimated_minutes=45,
        kind="ROADMAP",
        is_required=False,
        completed_at=None,
        topic_id=None,
        action_url="/roadmaps/topic/",
        action_label="Open topic",
        get_kind_display=lambda: "Roadmap",
    )
    summary = {
        "plan": object(),
        "recommendations": [completed, remaining],
        "total_count": 2,
        "completed_count": 1,
        "estimated_minutes": 65,
        "is_complete": False,
        "selection_status": "OPTIMAL",
        "selection_objective": 1.0,
        "selection_best_bound": 1.0,
        "selection_solve_time_ms": 1,
    }
    monkeypatch.setattr(
        "apps.core.dashboard_services.generate_daily_plan",
        lambda **kwargs: summary["plan"],
    )
    monkeypatch.setattr(
        "apps.core.dashboard_services.plan_summary",
        lambda **kwargs: summary,
    )

    result = _dashboard_plan(user=object(), now=_aware(2026, 8, 4))

    assert result["progress_percent"] == 50
    assert result["remaining_minutes"] == 45
    assert result["remaining_count"] == 1
    assert result["current"] is remaining
    assert result["focus_label"] == "Continue PostgreSQL"


def test_learning_journey_exposes_completed_current_next_and_later_states():
    user = get_user_model().objects.create_user(
        email="journey@example.com",
        password="safe-test-password",
    )
    roadmap = Roadmap.objects.create(
        title="Backend",
        slug="dashboard-v3-backend",
        description="",
        kind=Roadmap.Kind.ROLE,
        source=Roadmap.Source.CUSTOM,
        is_system=False,
        created_by=user,
    )
    topics = []
    for position, title in enumerate(("Foundations", "APIs", "Databases", "Testing"), start=1):
        section = RoadmapSection.objects.create(
            roadmap=roadmap,
            title=title,
            slug=title.lower(),
            position=position,
        )
        topic = RoadmapTopic.objects.create(
            section=section,
            title=f"{title} topic",
            slug=f"{title.lower()}-topic",
            position=1,
        )
        topics.append(topic)
    enrolment = UserRoadmap.objects.create(
        user=user,
        roadmap=roadmap,
        status=UserRoadmap.Status.IN_PROGRESS,
        is_focused=True,
    )
    UserTopicProgress.objects.create(
        user=user,
        topic=topics[0],
        status=UserTopicProgress.Status.COMPLETED,
        completed_at=timezone.now(),
    )
    UserTopicProgress.objects.create(
        user=user,
        topic=topics[1],
        status=UserTopicProgress.Status.IN_PROGRESS,
        started_at=timezone.now(),
    )

    roadmap = Roadmap.objects.prefetch_related("sections__topics").get(pk=roadmap.pk)
    journey = _learning_journey(
        user=user,
        roadmap_row={
            "roadmap": roadmap,
            "url": roadmap.get_absolute_url() if hasattr(roadmap, "get_absolute_url") else "/",
            "percentage": 25,
            "enrolment": enrolment,
        },
    )

    assert [section["state"] for section in journey["sections"]] == [
        "completed",
        "current",
        "next",
        "later",
    ]


def test_favourite_youtube_roadmap_is_included_in_dashboard_focus():
    user = get_user_model().objects.create_user(
        email="youtube-focus@example.com",
        password="safe-test-password",
    )
    roadmap = Roadmap.objects.create(
        title="System design playlist",
        slug="dashboard-v3-youtube",
        kind=Roadmap.Kind.PRACTICE,
        source=Roadmap.Source.YOUTUBE,
        learning_format=Roadmap.LearningFormat.VIDEO,
        is_system=False,
        created_by=user,
    )
    UserRoadmap.objects.create(
        user=user,
        roadmap=roadmap,
        status=UserRoadmap.Status.IN_PROGRESS,
        is_focused=False,
    )
    YouTubePlaylistRoadmap.objects.create(
        user=user,
        roadmap=roadmap,
        playlist_id="dashboard-v3-playlist",
        source_url="https://www.youtube.com/playlist?list=dashboard-v3",
        is_favourite=True,
    )

    rows = _focused_roadmaps(user=user)

    assert [row["roadmap"] for row in rows] == [roadmap]
    assert rows[0]["url"].endswith(f"/{roadmap.slug}/")


def test_upcoming_items_order_due_work_before_future_interview():
    user = get_user_model().objects.create_user(
        email="upcoming@example.com",
        password="safe-test-password",
    )
    goal = InterviewGoal.objects.create(
        user=user,
        title="Backend interview",
        goal_type=InterviewGoal.GoalType.SPECIFIC_OPPORTUNITY,
        role_title="Backend Engineer",
        status=InterviewGoal.Status.ACTIVE,
        is_primary=True,
    )
    InterviewStage.objects.create(
        goal=goal,
        stage_type=InterviewStage.StageType.TECHNICAL,
        scheduled_for=date(2026, 8, 5),
        is_current=True,
    )

    items = _upcoming_items(
        user=user,
        plan={"remaining_count": 2, "remaining_minutes": 70},
        review_summary={"due_count": 3},
        now=_aware(2026, 8, 4),
    )

    assert [item["kind"] for item in items] == ["Review", "Plan", "Interview"]


def test_calendar_marks_interview_dates_and_is_user_scoped():
    user = get_user_model().objects.create_user(
        email="calendar-owner@example.com",
        password="safe-test-password",
    )
    other_user = get_user_model().objects.create_user(
        email="calendar-other@example.com",
        password="safe-test-password",
    )
    goal = InterviewGoal.objects.create(
        user=user,
        title="Backend interview",
        goal_type=InterviewGoal.GoalType.SPECIFIC_OPPORTUNITY,
        role_title="Backend Engineer",
        company="Example",
        status=InterviewGoal.Status.ACTIVE,
        is_primary=True,
    )
    other_goal = InterviewGoal.objects.create(
        user=other_user,
        title="Private interview",
        goal_type=InterviewGoal.GoalType.GENERAL_PREPARATION,
        role_title="Private",
        status=InterviewGoal.Status.ACTIVE,
        is_primary=True,
    )
    InterviewStage.objects.create(
        goal=goal,
        stage_type=InterviewStage.StageType.TECHNICAL,
        scheduled_for=date(2026, 8, 15),
        is_current=True,
    )
    InterviewStage.objects.create(
        goal=other_goal,
        stage_type=InterviewStage.StageType.BEHAVIOURAL,
        scheduled_for=date(2026, 8, 16),
        is_current=True,
    )

    result = _calendar_data(
        user=user,
        month_value="2026-08",
        now=_aware(2026, 8, 4),
    )
    days = [day for week in result["weeks"] for day in week]
    fifteenth = next(day for day in days if day["date"] == date(2026, 8, 15))
    sixteenth = next(day for day in days if day["date"] == date(2026, 8, 16))

    assert fifteenth["has_interview"] is True
    assert "Backend interview" in fifteenth["event_label"]
    assert sixteenth["has_interview"] is False
