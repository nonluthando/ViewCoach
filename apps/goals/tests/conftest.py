import pytest

from apps.accounts.models import User
from apps.roadmaps.models import Roadmap, RoadmapSection, RoadmapTopic


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="goal-user@example.com",
        password="safe-test-password",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="other-goal-user@example.com",
        password="safe-test-password",
    )


@pytest.fixture
def roadmap(db):
    roadmap = Roadmap.objects.create(
        title="Backend Developer",
        slug="backend-developer-goal-test",
        description="Backend preparation",
        kind=Roadmap.Kind.ROLE,
        is_system=True,
        is_published=True,
    )
    section = RoadmapSection.objects.create(
        roadmap=roadmap,
        title="Foundations",
        slug="foundations",
        position=1,
    )
    for position, title in enumerate(["HTTP", "Databases", "Caching"], start=1):
        RoadmapTopic.objects.create(
            section=section,
            title=title,
            slug=title.lower(),
            position=position,
        )
    return roadmap
