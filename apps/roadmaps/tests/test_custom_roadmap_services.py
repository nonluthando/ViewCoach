import pytest

from apps.planner.candidate_builders import (
    _ordered_active_roadmap_enrolments,
)
from apps.roadmaps.custom_services import (
    create_custom_roadmap,
    create_custom_section,
    create_custom_topic,
    delete_custom_topic,
    move_custom_section,
    move_custom_topic,
    set_custom_roadmap_focus,
)
from apps.roadmaps.models import Roadmap, UserRoadmap

pytestmark = pytest.mark.django_db


def _roadmap(user, title="Spring Boot preparation"):
    return create_custom_roadmap(
        user=user,
        title=title,
        description="A private roadmap.",
        kind=Roadmap.Kind.SKILL,
    )


def _section(roadmap, title):
    return create_custom_section(
        roadmap=roadmap,
        title=title,
        description="",
    )


def _topic(section, title):
    return create_custom_topic(
        section=section,
        title=title,
        description="",
        external_url="",
        estimated_minutes=30,
    )


def test_create_custom_roadmap_sets_private_ownership(user):
    roadmap = _roadmap(user)

    assert roadmap.source == Roadmap.Source.CUSTOM
    assert roadmap.learning_format == Roadmap.LearningFormat.COURSE
    assert roadmap.created_by == user
    assert roadmap.is_system is False
    assert roadmap.is_published is True

    enrolment = UserRoadmap.objects.get(
        user=user,
        roadmap=roadmap,
    )
    assert enrolment.status == UserRoadmap.Status.NOT_STARTED
    assert enrolment.is_focused is False


def test_empty_custom_roadmap_cannot_enter_planner_focus(user):
    roadmap = _roadmap(user)

    with pytest.raises(ValueError, match="at least one topic"):
        set_custom_roadmap_focus(
            user=user,
            roadmap=roadmap,
            focused=True,
        )


def test_focused_custom_roadmap_is_planner_eligible(user):
    roadmap = _roadmap(user)
    section = _section(roadmap, "Framework foundations")
    _topic(section, "Dependency injection")

    enrolment = set_custom_roadmap_focus(
        user=user,
        roadmap=roadmap,
        focused=True,
    )
    candidates = _ordered_active_roadmap_enrolments(user=user)

    assert enrolment.status == UserRoadmap.Status.IN_PROGRESS
    assert enrolment.is_focused is True
    assert [item.roadmap_id for item in candidates] == [roadmap.pk]


def test_modules_and_topics_move_without_position_constraints(user):
    roadmap = _roadmap(user)
    first_section = _section(roadmap, "First")
    second_section = _section(roadmap, "Second")
    first_topic = _topic(first_section, "Alpha")
    second_topic = _topic(first_section, "Beta")

    moved_section = move_custom_section(
        roadmap=roadmap,
        section=second_section,
        direction="up",
    )
    moved_topic = move_custom_topic(
        section=first_section,
        topic=second_topic,
        direction="up",
    )

    first_section.refresh_from_db()
    second_section.refresh_from_db()
    first_topic.refresh_from_db()
    second_topic.refresh_from_db()

    assert moved_section is True
    assert second_section.position == 1
    assert first_section.position == 2
    assert moved_topic is True
    assert second_topic.position == 1
    assert first_topic.position == 2


def test_deleting_last_topic_removes_planner_focus(user):
    roadmap = _roadmap(user)
    section = _section(roadmap, "Only module")
    topic = _topic(section, "Only topic")
    set_custom_roadmap_focus(
        user=user,
        roadmap=roadmap,
        focused=True,
    )

    delete_custom_topic(user=user, topic=topic)

    enrolment = UserRoadmap.objects.get(
        user=user,
        roadmap=roadmap,
    )
    assert enrolment.status == UserRoadmap.Status.NOT_STARTED
    assert enrolment.is_focused is False
    assert enrolment.started_at is None
