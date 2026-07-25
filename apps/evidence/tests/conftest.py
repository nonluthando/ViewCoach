import pytest

from apps.accounts.models import User
from apps.evidence.models import EvidenceItem
from apps.goals.models import InterviewGoal
from apps.questions.models import TechnicalQuestion
from apps.roadmaps.models import Roadmap, RoadmapSection, RoadmapTopic


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="tee@example.com",
        password="safe-test-password",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="other@example.com",
        password="safe-test-password",
    )


@pytest.fixture
def evidence_item(user):
    return EvidenceItem.objects.create(
        owner=user,
        source_type=EvidenceItem.SourceType.PROJECT,
        title="ViewCoach",
        organisation="Personal project",
        summary="An interview preparation platform.",
        personal_contribution="Designed the Django architecture and review engine.",
        technologies="Python, Django, PostgreSQL",
    )


@pytest.fixture
def other_evidence(other_user):
    return EvidenceItem.objects.create(
        owner=other_user,
        source_type=EvidenceItem.SourceType.WORK,
        title="Private employer project",
    )


@pytest.fixture
def roadmap(db):
    return Roadmap.objects.create(
        title="Backend Developer",
        slug="backend-developer",
        description="Backend roadmap.",
        kind=Roadmap.Kind.ROLE,
        is_system=True,
        is_published=True,
    )


@pytest.fixture
def topic(roadmap):
    section = RoadmapSection.objects.create(
        roadmap=roadmap,
        title="Databases",
        slug="databases",
        position=1,
    )
    return RoadmapTopic.objects.create(
        section=section,
        title="Database constraints",
        slug="database-constraints",
        position=1,
    )


@pytest.fixture
def technical_question(user):
    return TechnicalQuestion.objects.create(
        owner=user,
        title="Explain a database constraint decision",
        prompt="Why use database constraints as well as form validation?",
        topic="Databases",
        intuition="Constraints protect invariants at the persistence boundary.",
    )


@pytest.fixture
def goal(user, roadmap):
    goal = InterviewGoal.objects.create(
        user=user,
        title="Backend interview",
        goal_type=InterviewGoal.GoalType.GENERAL_PREPARATION,
        role_title="Backend Developer",
        is_primary=True,
    )
    goal.roadmaps.add(roadmap)
    return goal
