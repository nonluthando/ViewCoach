import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.roadmaps.models import UserTopicProgress
from apps.roadmaps.youtube_client import (
    PlaylistPreview,
    PlaylistVideoPreview,
    YouTubeDataClient,
)
from apps.roadmaps.youtube_services import create_youtube_roadmap


pytestmark = pytest.mark.django_db


def build_preview():
    return PlaylistPreview(
        playlist_id="PL1234567890ABC",
        source_url=(
            "https://www.youtube.com/playlist?list=PL1234567890ABC"
        ),
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
                embeddable=True,
                made_for_kids=False,
            ),
        ),
    )


def create_user():
    return get_user_model().objects.create_user(
        email="tee@example.com",
        password="safe-password",
    )


def test_playlist_preview_requires_login(client):
    response = client.get(reverse("roadmaps:youtube_import"))
    assert response.status_code == 302


def test_user_can_preview_and_import_playlist(client, monkeypatch):
    user = create_user()
    client.force_login(user)
    preview = build_preview()
    monkeypatch.setattr(
        YouTubeDataClient,
        "fetch_playlist",
        lambda self, value: preview,
    )

    preview_response = client.post(
        reverse("roadmaps:youtube_import"),
        {"playlist_url": preview.source_url},
    )
    assert preview_response.status_code == 200
    assert "Spring Boot Course" in preview_response.content.decode()
    assert "Create roadmap" in preview_response.content.decode()

    create_response = client.post(
        reverse("roadmaps:youtube_import_confirm"),
        {"playlist_url": preview.source_url},
    )
    assert create_response.status_code == 302
    assert create_response.url.startswith("/roadmaps/")


def test_mark_watched_moves_to_next_video(client):
    user = create_user()
    client.force_login(user)
    source, _ = create_youtube_roadmap(
        user=user,
        preview=build_preview(),
    )
    videos = list(source.videos.select_related("topic").order_by("position"))

    response = client.post(
        reverse(
            "roadmaps:complete_youtube_video",
            kwargs={
                "slug": source.roadmap.slug,
                "topic_id": videos[0].topic_id,
            },
        )
    )

    assert response.status_code == 302
    assert response.url == reverse(
        "roadmaps:topic_detail",
        kwargs={
            "slug": source.roadmap.slug,
            "topic_id": videos[1].topic_id,
        },
    )
    progress = UserTopicProgress.objects.get(
        user=user,
        topic=videos[0].topic,
    )
    assert progress.status == UserTopicProgress.Status.COMPLETED


def test_user_can_remove_imported_playlist_without_touching_other_users(client):
    user = create_user()
    other_user = get_user_model().objects.create_user(
        email="other@example.com",
        password="safe-password",
    )
    source, _ = create_youtube_roadmap(
        user=user,
        preview=build_preview(),
    )
    other_source, _ = create_youtube_roadmap(
        user=other_user,
        preview=build_preview(),
    )
    client.force_login(user)

    response = client.post(
        reverse(
            "roadmaps:delete_youtube_roadmap",
            kwargs={"slug": source.roadmap.slug},
        )
    )

    assert response.status_code == 302
    assert not type(source).objects.filter(pk=source.pk).exists()
    assert type(other_source).objects.filter(pk=other_source.pk).exists()
