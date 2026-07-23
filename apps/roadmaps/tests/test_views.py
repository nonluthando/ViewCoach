import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.roadmaps.models import (
    Roadmap,
    RoadmapSection,
    RoadmapTopic,
    UserRoadmap,
    UserTopicProgress,
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
