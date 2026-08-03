import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.goals.forms import InterviewGoalForm
from apps.roadmaps.custom_services import (
    create_custom_roadmap,
    create_custom_section,
    create_custom_topic,
)
from apps.roadmaps.models import Roadmap, RoadmapSection, RoadmapTopic

pytestmark = pytest.mark.django_db


def _custom_roadmap(user, title="My Backend Path"):
    return create_custom_roadmap(
        user=user,
        title=title,
        description="Private interview preparation.",
        kind=Roadmap.Kind.ROLE,
    )


def test_custom_roadmap_list_requires_authentication(client):
    response = client.get(reverse("roadmaps:custom_list"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


def test_user_can_create_blank_custom_roadmap(client, user):
    client.force_login(user)

    response = client.post(
        reverse("roadmaps:custom_create"),
        {
            "title": "Spring Boot Interview Path",
            "description": "Prepare for junior Java roles.",
            "kind": Roadmap.Kind.SKILL,
        },
    )

    roadmap = Roadmap.objects.get(
        created_by=user,
        source=Roadmap.Source.CUSTOM,
    )
    assert response.status_code == 302
    assert response.url == reverse(
        "roadmaps:custom_manage",
        kwargs={"slug": roadmap.slug},
    )
    assert roadmap.sections.count() == 0


def test_editing_custom_roadmap_keeps_stable_slug(client, user):
    roadmap = _custom_roadmap(user)
    original_slug = roadmap.slug
    client.force_login(user)

    response = client.post(
        reverse(
            "roadmaps:custom_edit",
            kwargs={"slug": roadmap.slug},
        ),
        {
            "title": "Renamed Backend Path",
            "description": "Updated scope.",
            "kind": Roadmap.Kind.ROLE,
        },
    )

    roadmap.refresh_from_db()
    assert response.status_code == 302
    assert roadmap.title == "Renamed Backend Path"
    assert roadmap.slug == original_slug


def test_user_can_add_module_and_topic(client, user):
    roadmap = _custom_roadmap(user)
    client.force_login(user)

    section_response = client.post(
        reverse(
            "roadmaps:custom_section_create",
            kwargs={"slug": roadmap.slug},
        ),
        {
            "title": "Web framework",
            "description": "Core framework concepts.",
        },
    )
    section = RoadmapSection.objects.get(roadmap=roadmap)

    topic_response = client.post(
        reverse(
            "roadmaps:custom_topic_create",
            kwargs={
                "slug": roadmap.slug,
                "section_id": section.pk,
            },
        ),
        {
            "title": "Dependency injection",
            "description": "Explain inversion of control.",
            "external_url": "https://example.com/di",
            "estimated_minutes": 45,
        },
    )

    topic = RoadmapTopic.objects.get(section=section)
    assert section_response.status_code == 302
    assert topic_response.status_code == 302
    assert topic.title == "Dependency injection"
    assert topic.estimated_minutes == 45


def test_other_user_cannot_manage_private_custom_roadmap(client, user):
    roadmap = _custom_roadmap(user)
    other_user = User.objects.create_user(
        email="other@example.com",
        password="safe-test-password",
    )
    client.force_login(other_user)

    response = client.get(
        reverse(
            "roadmaps:custom_manage",
            kwargs={"slug": roadmap.slug},
        )
    )

    assert response.status_code == 404


def test_custom_roadmap_appears_in_goal_form(user):
    roadmap = _custom_roadmap(user)

    form = InterviewGoalForm(user=user)

    assert roadmap in form.fields["roadmaps"].queryset


def test_custom_roadmap_uses_shared_study_workspace(client, user):
    roadmap = _custom_roadmap(user)
    section = create_custom_section(
        roadmap=roadmap,
        title="Databases",
        description="",
    )
    topic = create_custom_topic(
        section=section,
        title="Transactions",
        description="",
        external_url="",
        estimated_minutes=30,
    )
    client.force_login(user)

    roadmap_response = client.get(
        reverse("roadmaps:detail", kwargs={"slug": roadmap.slug})
    )
    topic_response = client.get(
        reverse(
            "roadmaps:topic_detail",
            kwargs={
                "slug": roadmap.slug,
                "topic_id": topic.pk,
            },
        )
    )

    assert roadmap_response.status_code == 200
    assert "My roadmap" in roadmap_response.content.decode()
    assert reverse(
        "roadmaps:custom_manage",
        kwargs={"slug": roadmap.slug},
    ) in roadmap_response.content.decode()
    assert topic_response.status_code == 200
    assert "My roadmaps" in topic_response.content.decode()

def test_imported_course_is_not_treated_as_a_personal_roadmap(client, user):
    from apps.roadmaps.models import ExternalCourseRoadmap

    roadmap = Roadmap.objects.create(
        title="Imported course",
        slug="imported-course",
        kind=Roadmap.Kind.SKILL,
        source=Roadmap.Source.CUSTOM,
        learning_format=Roadmap.LearningFormat.COURSE,
        is_system=False,
        created_by=user,
    )
    ExternalCourseRoadmap.objects.create(
        user=user,
        roadmap=roadmap,
        provider=ExternalCourseRoadmap.Provider.OTHER,
        source_url="https://example.com/course",
    )
    client.force_login(user)

    list_response = client.get(reverse("roadmaps:custom_list"))
    manage_response = client.get(
        reverse("roadmaps:custom_manage", kwargs={"slug": roadmap.slug})
    )

    assert "Imported course" not in list_response.content.decode()
    assert manage_response.status_code == 404
