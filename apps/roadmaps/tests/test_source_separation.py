import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.roadmaps.models import Roadmap
from apps.roadmaps.services import (
    grouped_viewcoach_roadmap_cards,
    youtube_roadmap_cards,
)
from apps.roadmaps.youtube_client import (
    PlaylistPreview,
    PlaylistVideoPreview,
)
from apps.roadmaps.youtube_services import create_youtube_roadmap

pytestmark = pytest.mark.django_db


def create_user(email):
    return get_user_model().objects.create_user(
        email=email,
        password="safe-test-password",
    )


def build_preview(*, playlist_id="PL-SOURCE-TEST"):
    return PlaylistPreview(
        playlist_id=playlist_id,
        source_url=(f"https://www.youtube.com/playlist?list={playlist_id}"),
        title="Backend Engineering Playlist",
        description="",
        channel_title="Example Channel",
        thumbnail_url="https://i.ytimg.com/example.jpg",
        videos=(
            PlaylistVideoPreview(
                playlist_item_id=f"{playlist_id}-item-1",
                video_id=f"{playlist_id}-video-1",
                title="HTTP Fundamentals",
                channel_title="Example Channel",
                thumbnail_url="https://i.ytimg.com/1.jpg",
                duration_seconds=600,
                position=0,
                available=True,
                embeddable=True,
                made_for_kids=False,
            ),
        ),
    )


def create_viewcoach_roadmap():
    return Roadmap.objects.create(
        title="Backend Development",
        slug="backend-development",
        description="A curated backend path.",
        kind=Roadmap.Kind.ROLE,
        source=Roadmap.Source.VIEWCOACH,
        is_system=True,
        is_published=True,
    )


def test_roadmap_defaults_to_viewcoach_source():
    roadmap = Roadmap.objects.create(
        title="Python",
        slug="python",
        kind=Roadmap.Kind.SKILL,
    )

    assert roadmap.source == Roadmap.Source.VIEWCOACH


def test_youtube_import_sets_explicit_source():
    user = create_user("youtube-source@example.com")

    source, _ = create_youtube_roadmap(
        user=user,
        preview=build_preview(),
    )

    source.roadmap.refresh_from_db()
    assert source.roadmap.source == Roadmap.Source.YOUTUBE


def test_source_specific_services_do_not_mix_catalogues():
    user = create_user("catalogues@example.com")
    viewcoach = create_viewcoach_roadmap()
    youtube, _ = create_youtube_roadmap(
        user=user,
        preview=build_preview(),
    )

    viewcoach_groups = grouped_viewcoach_roadmap_cards(user=user)
    viewcoach_ids = {item["roadmap"].pk for group in viewcoach_groups for item in group["items"]}
    youtube_ids = {item["roadmap"].pk for item in youtube_roadmap_cards(user=user)}

    assert viewcoach.pk in viewcoach_ids
    assert youtube.roadmap_id not in viewcoach_ids
    assert youtube.roadmap_id in youtube_ids
    assert viewcoach.pk not in youtube_ids


def test_viewcoach_and_youtube_pages_are_visually_separate(client):
    user = create_user("separate-pages@example.com")
    viewcoach = create_viewcoach_roadmap()
    youtube, _ = create_youtube_roadmap(
        user=user,
        preview=build_preview(),
    )
    client.force_login(user)

    viewcoach_response = client.get(reverse("roadmaps:list"))
    youtube_response = client.get(reverse("roadmaps:youtube_list"))

    assert viewcoach_response.status_code == 200
    assert youtube_response.status_code == 200
    assert viewcoach.title in viewcoach_response.content.decode()
    assert youtube.roadmap.title not in viewcoach_response.content.decode()
    assert youtube.roadmap.title in youtube_response.content.decode()
    assert viewcoach.title not in youtube_response.content.decode()


def test_youtube_library_is_owner_scoped(client):
    user = create_user("owner@example.com")
    other_user = create_user("other-owner@example.com")
    own_source, _ = create_youtube_roadmap(
        user=user,
        preview=build_preview(playlist_id="PL-OWN"),
    )
    other_source, _ = create_youtube_roadmap(
        user=other_user,
        preview=build_preview(playlist_id="PL-OTHER"),
    )
    client.force_login(user)

    response = client.get(reverse("roadmaps:youtube_list"))
    content = response.content.decode()

    assert own_source.roadmap.title in content
    assert (
        reverse(
            "roadmaps:youtube_detail",
            args=[own_source.roadmap.slug],
        )
        in content
    )
    assert other_source.roadmap.slug not in content


def test_legacy_youtube_detail_redirects_to_canonical_route(client):
    user = create_user("legacy-route@example.com")
    source, _ = create_youtube_roadmap(
        user=user,
        preview=build_preview(),
    )
    client.force_login(user)

    response = client.get(reverse("roadmaps:detail", args=[source.roadmap.slug]))

    assert response.status_code == 302
    assert response.url == reverse(
        "roadmaps:youtube_detail",
        args=[source.roadmap.slug],
    )


def test_user_cannot_open_another_users_youtube_detail(client):
    user = create_user("viewer@example.com")
    other_user = create_user("private-owner@example.com")
    source, _ = create_youtube_roadmap(
        user=other_user,
        preview=build_preview(),
    )
    client.force_login(user)

    response = client.get(reverse("roadmaps:youtube_detail", args=[source.roadmap.slug]))

    assert response.status_code == 404


def test_youtube_notes_return_to_youtube_workspace(client):
    user = create_user("notes-route@example.com")
    source, _ = create_youtube_roadmap(
        user=user,
        preview=build_preview(),
    )
    video = source.videos.select_related("topic").get()
    client.force_login(user)

    response = client.post(
        reverse(
            "roadmaps:save_topic_notes",
            args=[source.roadmap.slug, video.topic_id],
        ),
        {"notes": "HTTP requests contain a method, path and headers."},
    )

    assert response.status_code == 302
    assert response.url == reverse(
        "roadmaps:youtube_video_detail",
        args=[source.roadmap.slug, video.topic_id],
    )
