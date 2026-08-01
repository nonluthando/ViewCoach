import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)


MIGRATE_FROM = [("roadmaps", "0003_youtube_playlist_roadmaps")]
MIGRATE_TO = [("roadmaps", "0004_roadmap_source")]


def test_roadmap_source_backfill_preserves_existing_records():
    executor = MigrationExecutor(connection)
    executor.migrate(MIGRATE_FROM)
    old_apps = executor.loader.project_state(MIGRATE_FROM).apps

    User = old_apps.get_model("accounts", "User")
    Roadmap = old_apps.get_model("roadmaps", "Roadmap")
    RoadmapSection = old_apps.get_model("roadmaps", "RoadmapSection")
    RoadmapTopic = old_apps.get_model("roadmaps", "RoadmapTopic")
    UserTopicProgress = old_apps.get_model(
        "roadmaps",
        "UserTopicProgress",
    )
    YouTubePlaylistRoadmap = old_apps.get_model(
        "roadmaps",
        "YouTubePlaylistRoadmap",
    )

    user = User.objects.create(
        email="source-migration@example.com",
        password="",
    )
    built_in = Roadmap.objects.create(
        title="Backend Development",
        slug="backend-development-migration",
        kind="ROLE",
        is_system=True,
        is_published=True,
    )
    custom = Roadmap.objects.create(
        title="My Learning Path",
        slug="my-learning-path-migration",
        kind="SKILL",
        is_system=False,
        is_published=True,
        created_by_id=user.pk,
    )
    youtube = Roadmap.objects.create(
        title="YouTube Course",
        slug="youtube-course-migration",
        kind="SKILL",
        is_system=False,
        is_published=True,
        created_by_id=user.pk,
    )
    section = RoadmapSection.objects.create(
        roadmap_id=youtube.pk,
        title="Playlist videos",
        slug="playlist-videos",
    )
    topic = RoadmapTopic.objects.create(
        section_id=section.pk,
        title="Introduction",
        slug="introduction",
    )
    progress = UserTopicProgress.objects.create(
        user_id=user.pk,
        topic_id=topic.pk,
        status="IN_PROGRESS",
        notes="Existing notes must survive the source backfill.",
    )
    YouTubePlaylistRoadmap.objects.create(
        user_id=user.pk,
        roadmap_id=youtube.pk,
        playlist_id="PL-MIGRATION",
        source_url=("https://www.youtube.com/playlist?list=PL-MIGRATION"),
    )

    executor = MigrationExecutor(connection)
    executor.migrate(MIGRATE_TO)
    new_apps = executor.loader.project_state(MIGRATE_TO).apps
    NewRoadmap = new_apps.get_model("roadmaps", "Roadmap")
    NewProgress = new_apps.get_model("roadmaps", "UserTopicProgress")

    assert NewRoadmap.objects.get(pk=built_in.pk).source == "VIEWCOACH"
    assert NewRoadmap.objects.get(pk=custom.pk).source == "CUSTOM"
    assert NewRoadmap.objects.get(pk=youtube.pk).source == "YOUTUBE"

    migrated_progress = NewProgress.objects.get(pk=progress.pk)
    assert migrated_progress.status == "IN_PROGRESS"
    assert migrated_progress.notes == ("Existing notes must survive the source backfill.")
