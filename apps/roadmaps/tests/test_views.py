import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.roadmaps.models import (
    Roadmap,
    RoadmapSection,
    RoadmapTopic,
    UserRoadmap,
    UserTopicProgress,
    UserTopicResource,
)

pytestmark = pytest.mark.django_db


def test_roadmap_catalogue_requires_login(client):
    response = client.get(reverse("roadmaps:list"))

    assert response.status_code == 302


def test_catalogue_lists_published_roadmaps(client, user, roadmap):
    Roadmap.objects.create(
        title="Draft roadmap",
        slug="draft-roadmap",
        kind=Roadmap.Kind.SKILL,
        is_published=False,
        position=2,
    )
    client.force_login(user)

    response = client.get(reverse("roadmaps:list"))

    content = response.content.decode()
    assert response.status_code == 200
    assert roadmap.title in content
    assert "Draft roadmap" not in content


def test_catalogue_hides_another_users_custom_roadmap(client, user, roadmap):
    other_user = User.objects.create_user(
        email="other@example.com",
        password="safe-test-password",
    )
    Roadmap.objects.create(
        title="Private custom path",
        slug="private-custom-path",
        kind=Roadmap.Kind.SKILL,
        is_system=False,
        created_by=other_user,
        is_published=True,
        position=2,
    )
    client.force_login(user)

    response = client.get(reverse("roadmaps:list"))

    assert roadmap.title in response.content.decode()
    assert "Private custom path" not in response.content.decode()


def test_detail_shows_sections_topics_and_progress(client, user, roadmap, section, topic):
    client.force_login(user)

    response = client.get(reverse("roadmaps:detail", args=[roadmap.slug]))

    content = response.content.decode()
    assert response.status_code == 200
    assert section.title in content
    assert topic.title in content
    assert response.context["progress"]["total_count"] == 1


def test_start_roadmap_creates_active_enrolment(client, user, roadmap):
    client.force_login(user)

    response = client.post(reverse("roadmaps:start", args=[roadmap.slug]))

    assert response.status_code == 302
    enrolment = UserRoadmap.objects.get(user=user, roadmap=roadmap)
    assert enrolment.status == UserRoadmap.Status.IN_PROGRESS
    assert enrolment.started_at is not None


def test_updating_topic_status_creates_progress_and_enrolment(
    client,
    user,
    roadmap,
    topic,
):
    client.force_login(user)

    response = client.post(
        reverse(
            "roadmaps:update_topic_status",
            args=[roadmap.slug, topic.pk],
        ),
        {"status": UserTopicProgress.Status.COMPLETED},
    )

    assert response.status_code == 302
    assert response.url.endswith(f"#topic-{topic.pk}")
    progress = UserTopicProgress.objects.get(user=user, topic=topic)
    assert progress.status == UserTopicProgress.Status.COMPLETED
    assert progress.started_at is not None
    assert progress.completed_at is not None
    assert UserRoadmap.objects.get(user=user, roadmap=roadmap).status == (
        UserRoadmap.Status.COMPLETED
    )


def test_resetting_topic_clears_completion_timestamps(client, user, roadmap, topic):
    client.force_login(user)
    update_url = reverse(
        "roadmaps:update_topic_status",
        args=[roadmap.slug, topic.pk],
    )
    client.post(update_url, {"status": UserTopicProgress.Status.COMPLETED})

    client.post(update_url, {"status": UserTopicProgress.Status.NOT_STARTED})

    progress = UserTopicProgress.objects.get(user=user, topic=topic)
    assert progress.status == UserTopicProgress.Status.NOT_STARTED
    assert progress.started_at is None
    assert progress.completed_at is None


def test_topic_from_another_roadmap_cannot_be_updated(client, user, roadmap, topic):
    other_roadmap = Roadmap.objects.create(
        title="Java",
        slug="java",
        kind=Roadmap.Kind.SKILL,
        position=2,
    )
    other_section = RoadmapSection.objects.create(
        roadmap=other_roadmap,
        title="Core Java",
        slug="core-java",
        position=1,
    )
    other_topic = RoadmapTopic.objects.create(
        section=other_section,
        title="Strings",
        slug="strings",
        position=1,
    )
    client.force_login(user)

    response = client.post(
        reverse(
            "roadmaps:update_topic_status",
            args=[roadmap.slug, other_topic.pk],
        ),
        {"status": UserTopicProgress.Status.COMPLETED},
    )

    assert response.status_code == 404
    assert not UserTopicProgress.objects.filter(user=user, topic=other_topic).exists()


def test_unpublished_roadmap_is_not_accessible(client, user):
    roadmap = Roadmap.objects.create(
        title="Draft roadmap",
        slug="draft-roadmap",
        kind=Roadmap.Kind.SKILL,
        is_published=False,
    )
    client.force_login(user)

    response = client.get(reverse("roadmaps:detail", args=[roadmap.slug]))

    assert response.status_code == 404


def test_topic_workspace_requires_login(client, roadmap, topic):
    response = client.get(
        reverse("roadmaps:topic_detail", args=[roadmap.slug, topic.pk])
    )

    assert response.status_code == 302


def test_topic_workspace_shows_notes_resources_and_status(
    client,
    user,
    roadmap,
    topic,
):
    progress = UserTopicProgress.objects.create(
        user=user,
        topic=topic,
        status=UserTopicProgress.Status.IN_PROGRESS,
        notes="Remember indexes and query plans.",
    )
    UserTopicResource.objects.create(
        user=user,
        topic=topic,
        title="PostgreSQL documentation",
        url="https://www.postgresql.org/docs/",
    )
    client.force_login(user)

    response = client.get(
        reverse("roadmaps:topic_detail", args=[roadmap.slug, topic.pk])
    )

    content = response.content.decode()
    assert response.status_code == 200
    assert "Study notes" in content
    assert "Remember indexes and query plans." in content
    assert "PostgreSQL documentation" in content
    assert response.context["progress"] == progress
    assert response.context["current_status"] == (
        UserTopicProgress.Status.IN_PROGRESS
    )


def test_topic_navigation_crosses_section_boundaries(
    client,
    user,
    roadmap,
    section,
    topic,
):
    next_section = RoadmapSection.objects.create(
        roadmap=roadmap,
        title="APIs",
        slug="apis",
        position=2,
    )
    next_topic = RoadmapTopic.objects.create(
        section=next_section,
        title="REST API design",
        slug="rest-api-design",
        position=1,
    )
    client.force_login(user)

    first_response = client.get(
        reverse("roadmaps:topic_detail", args=[roadmap.slug, topic.pk])
    )
    second_response = client.get(
        reverse("roadmaps:topic_detail", args=[roadmap.slug, next_topic.pk])
    )

    assert first_response.context["previous_topic"] is None
    assert first_response.context["next_topic"] == next_topic
    assert first_response.context["topic_number"] == 1
    assert first_response.context["topic_count"] == 2
    assert second_response.context["previous_topic"] == topic
    assert second_response.context["next_topic"] is None


def test_topic_workspace_rejects_topic_from_another_roadmap(
    client,
    user,
    roadmap,
):
    other_roadmap = Roadmap.objects.create(
        title="Python",
        slug="python",
        kind=Roadmap.Kind.SKILL,
        position=2,
    )
    other_section = RoadmapSection.objects.create(
        roadmap=other_roadmap,
        title="Core Python",
        slug="core-python",
        position=1,
    )
    other_topic = RoadmapTopic.objects.create(
        section=other_section,
        title="Functions",
        slug="functions",
        position=1,
    )
    client.force_login(user)

    response = client.get(
        reverse("roadmaps:topic_detail", args=[roadmap.slug, other_topic.pk])
    )

    assert response.status_code == 404


def test_saving_topic_notes_creates_private_progress(
    client,
    user,
    roadmap,
    topic,
):
    client.force_login(user)

    response = client.post(
        reverse("roadmaps:save_topic_notes", args=[roadmap.slug, topic.pk]),
        {"notes": "Use EXPLAIN ANALYZE when checking a slow query."},
    )

    assert response.status_code == 302
    progress = UserTopicProgress.objects.get(user=user, topic=topic)
    assert progress.notes == "Use EXPLAIN ANALYZE when checking a slow query."
    assert progress.status == UserTopicProgress.Status.NOT_STARTED


def test_adding_topic_resource_assigns_user_and_topic(
    client,
    user,
    roadmap,
    topic,
):
    client.force_login(user)

    response = client.post(
        reverse("roadmaps:add_topic_resource", args=[roadmap.slug, topic.pk]),
        {
            "title": "PostgreSQL documentation",
            "url": "https://www.postgresql.org/docs/",
        },
    )

    assert response.status_code == 302
    resource = UserTopicResource.objects.get()
    assert resource.user == user
    assert resource.topic == topic
    assert resource.title == "PostgreSQL documentation"


def test_duplicate_topic_resource_url_is_not_added_twice(
    client,
    user,
    roadmap,
    topic,
):
    client.force_login(user)
    resource_url = reverse(
        "roadmaps:add_topic_resource",
        args=[roadmap.slug, topic.pk],
    )
    payload = {
        "title": "PostgreSQL documentation",
        "url": "https://www.postgresql.org/docs/",
    }

    client.post(resource_url, payload)
    client.post(resource_url, payload)

    assert UserTopicResource.objects.filter(user=user, topic=topic).count() == 1


def test_topic_workspace_hides_another_users_resources(
    client,
    user,
    roadmap,
    topic,
):
    other_user = User.objects.create_user(
        email="resource-owner@example.com",
        password="safe-test-password",
    )
    UserTopicResource.objects.create(
        user=other_user,
        topic=topic,
        title="Private study link",
        url="https://example.com/private-study-link",
    )
    client.force_login(user)

    response = client.get(
        reverse("roadmaps:topic_detail", args=[roadmap.slug, topic.pk])
    )

    assert "Private study link" not in response.content.decode()


def test_user_cannot_delete_another_users_topic_resource(
    client,
    user,
    roadmap,
    topic,
):
    other_user = User.objects.create_user(
        email="another-resource-owner@example.com",
        password="safe-test-password",
    )
    resource = UserTopicResource.objects.create(
        user=other_user,
        topic=topic,
        title="Private study link",
        url="https://example.com/private-study-link",
    )
    client.force_login(user)

    response = client.post(
        reverse(
            "roadmaps:delete_topic_resource",
            args=[roadmap.slug, topic.pk, resource.pk],
        )
    )

    assert response.status_code == 404
    assert UserTopicResource.objects.filter(pk=resource.pk).exists()


def test_status_update_can_return_to_topic_workspace(
    client,
    user,
    roadmap,
    topic,
):
    client.force_login(user)

    response = client.post(
        reverse(
            "roadmaps:update_topic_status",
            args=[roadmap.slug, topic.pk],
        ),
        {
            "status": UserTopicProgress.Status.IN_PROGRESS,
            "return_to": "topic",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse(
        "roadmaps:topic_detail",
        args=[roadmap.slug, topic.pk],
    )
