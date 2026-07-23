import pytest
from django.db import IntegrityError, transaction

from apps.roadmaps.models import (
    UserRoadmap,
    UserTopicProgress,
    UserTopicResource,
)

pytestmark = pytest.mark.django_db


def test_user_can_only_enrol_in_roadmap_once(user, roadmap):
    UserRoadmap.objects.create(user=user, roadmap=roadmap)

    with pytest.raises(IntegrityError), transaction.atomic():
        UserRoadmap.objects.create(user=user, roadmap=roadmap)


def test_user_has_one_progress_record_per_topic(user, topic):
    UserTopicProgress.objects.create(user=user, topic=topic)

    with pytest.raises(IntegrityError), transaction.atomic():
        UserTopicProgress.objects.create(user=user, topic=topic)


def test_topic_exposes_parent_roadmap(topic, roadmap):
    assert topic.roadmap == roadmap


def test_topic_resource_belongs_to_one_user_and_topic(user, topic):
    resource = UserTopicResource.objects.create(
        user=user,
        topic=topic,
        title="PostgreSQL documentation",
        url="https://www.postgresql.org/docs/",
    )

    assert resource.user == user
    assert resource.topic == topic
    assert "PostgreSQL documentation" in str(resource)
