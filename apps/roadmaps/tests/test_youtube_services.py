import pytest
from django.contrib.auth import get_user_model

from apps.roadmaps.models import (
    Roadmap,
    RoadmapTopic,
    YouTubePlaylistRoadmap,
    YouTubePlaylistVideo,
)
from apps.roadmaps.youtube_client import (
    PlaylistPreview,
    PlaylistVideoPreview,
)
from apps.roadmaps.youtube_services import create_youtube_roadmap

pytestmark = pytest.mark.django_db


def build_preview():
    return PlaylistPreview(
        playlist_id="PL1234567890ABC",
        source_url=("https://www.youtube.com/playlist?list=PL1234567890ABC"),
        title="Spring Boot Course",
        description="",
        channel_title="Example Channel",
        thumbnail_url="https://i.ytimg.com/example.jpg",
        videos=(
            PlaylistVideoPreview(
                playlist_item_id="item-1",
                video_id="video-1",
                title="Introduction",
                channel_title="Example Channel",
                thumbnail_url="https://i.ytimg.com/1.jpg",
                duration_seconds=600,
                position=0,
                available=True,
                embeddable=True,
                made_for_kids=False,
            ),
            PlaylistVideoPreview(
                playlist_item_id="item-2",
                video_id="video-2",
                title="Dependency Injection",
                channel_title="Example Channel",
                thumbnail_url="https://i.ytimg.com/2.jpg",
                duration_seconds=900,
                position=1,
                available=True,
                embeddable=False,
                made_for_kids=False,
            ),
            PlaylistVideoPreview(
                playlist_item_id="item-3",
                video_id="video-3",
                title="Private video",
                channel_title="",
                thumbnail_url="",
                duration_seconds=0,
                position=2,
                available=False,
                embeddable=False,
                made_for_kids=None,
            ),
        ),
    )


def test_create_youtube_roadmap_preserves_order_and_unavailable_items():
    user = get_user_model().objects.create_user(
        email="tee@example.com",
        password="safe-password",
    )

    source, created = create_youtube_roadmap(
        user=user,
        preview=build_preview(),
    )

    assert created is True
    assert source.roadmap.created_by == user
    assert source.roadmap.is_system is False
    assert source.roadmap.source == Roadmap.Source.YOUTUBE
    assert source.available_video_count == 2
    assert source.unavailable_video_count == 1
    assert list(
        RoadmapTopic.objects.filter(section__roadmap=source.roadmap).values_list("title", flat=True)
    ) == ["Introduction", "Dependency Injection"]
    assert YouTubePlaylistVideo.objects.filter(playlist=source).count() == 3
    assert (
        YouTubePlaylistVideo.objects.get(
            playlist=source,
            playlist_item_id="item-3",
        ).topic
        is None
    )


def test_duplicate_playlist_returns_existing_roadmap():
    user = get_user_model().objects.create_user(
        email="tee@example.com",
        password="safe-password",
    )
    first, first_created = create_youtube_roadmap(
        user=user,
        preview=build_preview(),
    )
    second, second_created = create_youtube_roadmap(
        user=user,
        preview=build_preview(),
    )

    assert first_created is True
    assert second_created is False
    assert second.pk == first.pk
    assert YouTubePlaylistRoadmap.objects.count() == 1
