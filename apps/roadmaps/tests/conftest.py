import pytest

from apps.accounts.models import User
from apps.roadmaps.models import Roadmap, RoadmapSection, RoadmapTopic


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="tee@example.com",
        password="safe-test-password",
    )


@pytest.fixture
def roadmap(db):
    return Roadmap.objects.create(
        title="Backend Developer",
        slug="backend-developer",
        description="Learn backend development.",
        kind=Roadmap.Kind.ROLE,
        position=1,
    )


@pytest.fixture
def section(roadmap):
    return RoadmapSection.objects.create(
        roadmap=roadmap,
        title="Databases",
        slug="databases",
        position=1,
    )


@pytest.fixture
def topic(section):
    return RoadmapTopic.objects.create(
        section=section,
        title="PostgreSQL",
        slug="postgresql",
        position=1,
    )
