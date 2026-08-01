import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.roadmaps.models import (
    Roadmap,
    UserRoadmap,
    YouTubeRoadmapGroup,
)
from apps.roadmaps.services import (
    MAX_FAVOURITE_YOUTUBE_ROADMAPS,
    MAX_FOCUSED_VIEWCOACH_ROADMAPS,
    RoadmapSelectionLimitError,
    set_viewcoach_roadmap_focus,
    set_youtube_roadmap_favourite,
)
from apps.roadmaps.youtube_client import PlaylistPreview, PlaylistVideoPreview
from apps.roadmaps.youtube_services import create_youtube_roadmap

pytestmark = pytest.mark.django_db


def create_user(email="tee@example.com"):
    return get_user_model().objects.create_user(
        email=email,
        password="safe-password",
    )


def create_viewcoach_roadmap(position):
    return Roadmap.objects.create(
        title=f"Roadmap {position}",
        slug=f"roadmap-{position}",
        description="",
        kind=Roadmap.Kind.SKILL,
        source=Roadmap.Source.VIEWCOACH,
        position=position,
        is_system=True,
        is_published=True,
    )


def preview(number):
    return PlaylistPreview(
        playlist_id=f"PL{number:014d}",
        source_url=f"https://www.youtube.com/playlist?list=PL{number:014d}",
        title=f"Course {number}",
        description="",
        channel_title="Example Channel",
        thumbnail_url="",
        videos=(
            PlaylistVideoPreview(
                playlist_item_id=f"item-{number}",
                video_id=f"video-{number}",
                title="Lesson",
                channel_title="Example Channel",
                thumbnail_url="",
                duration_seconds=600,
                position=0,
                available=True,
                embeddable=True,
                made_for_kids=False,
            ),
        ),
    )


def test_only_four_viewcoach_roadmaps_can_be_focused():
    user = create_user()
    roadmaps = [create_viewcoach_roadmap(index) for index in range(5)]

    for roadmap in roadmaps[:MAX_FOCUSED_VIEWCOACH_ROADMAPS]:
        set_viewcoach_roadmap_focus(user=user, roadmap=roadmap, focused=True)

    with pytest.raises(RoadmapSelectionLimitError):
        set_viewcoach_roadmap_focus(user=user, roadmap=roadmaps[-1], focused=True)

    assert UserRoadmap.objects.filter(user=user, is_focused=True).count() == 4


def test_unfocusing_preserves_enrolment_and_progress_state():
    user = create_user()
    roadmap = create_viewcoach_roadmap(1)
    enrolment = set_viewcoach_roadmap_focus(user=user, roadmap=roadmap, focused=True)

    set_viewcoach_roadmap_focus(user=user, roadmap=roadmap, focused=False)

    enrolment.refresh_from_db()
    assert enrolment.status == UserRoadmap.Status.IN_PROGRESS
    assert enrolment.is_focused is False


def test_only_five_youtube_roadmaps_can_be_favourited():
    user = create_user()
    sources = [create_youtube_roadmap(user=user, preview=preview(index))[0] for index in range(6)]

    assert sum(source.is_favourite for source in sources) == MAX_FAVOURITE_YOUTUBE_ROADMAPS
    with pytest.raises(RoadmapSelectionLimitError):
        set_youtube_roadmap_favourite(
            user=user,
            source=sources[-1],
            favourite=True,
        )


def test_deleting_group_moves_playlist_to_ungrouped(client):
    user = create_user()
    source, _ = create_youtube_roadmap(user=user, preview=preview(1))
    group = YouTubeRoadmapGroup.objects.create(user=user, name="Backend")
    source.group = group
    source.save(update_fields=["group", "updated_at"])
    client.force_login(user)

    response = client.post(reverse("roadmaps:youtube_group_delete", kwargs={"group_id": group.pk}))

    assert response.status_code == 302
    source.refresh_from_db()
    assert source.group is None


def test_user_cannot_move_playlist_into_another_users_group(client):
    user = create_user()
    other = create_user("other@example.com")
    source, _ = create_youtube_roadmap(user=user, preview=preview(1))
    other_group = YouTubeRoadmapGroup.objects.create(user=other, name="Private")
    client.force_login(user)

    response = client.post(
        reverse("roadmaps:youtube_move", kwargs={"slug": source.roadmap.slug}),
        {"group_id": other_group.pk},
    )

    assert response.status_code == 404
