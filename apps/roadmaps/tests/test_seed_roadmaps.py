import pytest
from django.core.management import call_command

from apps.roadmaps.models import Roadmap, RoadmapTopic

pytestmark = pytest.mark.django_db


def test_seed_command_creates_full_builtin_catalogue():
    call_command("seed_roadmaps")

    assert Roadmap.objects.count() == 12
    assert Roadmap.objects.filter(kind=Roadmap.Kind.ROLE).count() == 4
    assert Roadmap.objects.filter(kind=Roadmap.Kind.SKILL).count() == 7
    assert Roadmap.objects.filter(kind=Roadmap.Kind.PRACTICE).count() == 1
    assert RoadmapTopic.objects.count() == 419
    assert Roadmap.objects.filter(slug="system-design").exists()
    assert Roadmap.objects.filter(slug="data-structures-algorithms").exists()
    assert Roadmap.objects.filter(slug="leetcode-interview-practice").exists()


def test_seed_command_is_idempotent():
    call_command("seed_roadmaps")
    call_command("seed_roadmaps")

    assert Roadmap.objects.count() == 12
    assert RoadmapTopic.objects.count() == 419
