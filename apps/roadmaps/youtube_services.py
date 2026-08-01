from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from .models import (
    Roadmap,
    RoadmapSection,
    RoadmapTopic,
    YouTubePlaylistRoadmap,
    YouTubePlaylistVideo,
)
from .services import MAX_FAVOURITE_YOUTUBE_ROADMAPS
from .youtube_client import PlaylistPreview, PlaylistVideoPreview, format_duration


def _unique_roadmap_slug(*, title, playlist_id):
    base = slugify(title)[:120] or "youtube-playlist"
    identifier = slugify(playlist_id)[:24] or "course"
    candidate = f"{base}-{identifier}"[:160]
    suffix = 2
    while Roadmap.objects.filter(slug=candidate).exists():
        ending = f"-{suffix}"
        candidate = f"{base[: 160 - len(identifier) - len(ending) - 1]}-{identifier}{ending}"
        suffix += 1
    return candidate


def _unique_topic_slug(*, section, video):
    base = slugify(f"{video.position + 1}-{video.title}")[:165]
    if not base:
        base = f"video-{video.position + 1}"
    candidate = base
    suffix = 2
    while RoadmapTopic.objects.filter(section=section, slug=candidate).exists():
        ending = f"-{suffix}"
        candidate = f"{base[: 180 - len(ending)]}{ending}"
        suffix += 1
    return candidate


def _topic_description(video: PlaylistVideoPreview):
    parts = [format_duration(video.duration_seconds)]
    if video.channel_title:
        parts.append(video.channel_title)
    if not video.embeddable:
        parts.append("Opens on YouTube")
    return " · ".join(parts)


def _roadmap_description(preview: PlaylistPreview):
    source = f" by {preview.channel_title}" if preview.channel_title else ""
    return (
        f"Imported from a YouTube playlist{source}. "
        f"{preview.available_video_count} available videos, "
        f"{preview.total_duration_display} total video length."
    )


def _create_topic(*, section, video):
    return RoadmapTopic.objects.create(
        section=section,
        title=video.title[:160],
        slug=_unique_topic_slug(section=section, video=video),
        description=_topic_description(video),
        position=video.position,
    )


@transaction.atomic
def create_youtube_roadmap(*, user, preview: PlaylistPreview):
    if not preview.available_video_count:
        raise ValueError("This playlist has no available videos to import.")

    existing = (
        YouTubePlaylistRoadmap.objects.filter(
            user=user,
            playlist_id=preview.playlist_id,
        )
        .select_related("roadmap")
        .first()
    )
    if existing:
        return existing, False

    should_favourite = (
        YouTubePlaylistRoadmap.objects.filter(
            user=user,
            is_favourite=True,
            roadmap__source=Roadmap.Source.YOUTUBE,
        ).count()
        < MAX_FAVOURITE_YOUTUBE_ROADMAPS
    )

    roadmap = Roadmap.objects.create(
        title=preview.title[:140],
        slug=_unique_roadmap_slug(
            title=preview.title,
            playlist_id=preview.playlist_id,
        ),
        description=_roadmap_description(preview),
        kind=Roadmap.Kind.SKILL,
        source=Roadmap.Source.YOUTUBE,
        position=1000,
        is_system=False,
        is_published=True,
        created_by=user,
    )
    section = RoadmapSection.objects.create(
        roadmap=roadmap,
        title="Playlist videos",
        slug="playlist-videos",
        description=("Work through the videos in their original YouTube playlist order."),
        position=0,
    )
    source = YouTubePlaylistRoadmap.objects.create(
        user=user,
        roadmap=roadmap,
        is_favourite=should_favourite,
        playlist_id=preview.playlist_id,
        source_url=preview.source_url,
        channel_title=preview.channel_title[:200],
        thumbnail_url=preview.thumbnail_url,
        video_count=preview.video_count,
        available_video_count=preview.available_video_count,
        unavailable_video_count=preview.unavailable_video_count,
        total_duration_seconds=preview.total_duration_seconds,
        last_synced_at=timezone.now(),
    )

    for video in preview.videos:
        topic = _create_topic(section=section, video=video) if video.available else None
        YouTubePlaylistVideo.objects.create(
            playlist=source,
            topic=topic,
            playlist_item_id=video.playlist_item_id,
            video_id=video.video_id,
            title=video.title[:300],
            channel_title=video.channel_title[:200],
            thumbnail_url=video.thumbnail_url,
            duration_seconds=video.duration_seconds,
            position=video.position,
            available=video.available,
            embeddable=video.embeddable,
            made_for_kids=video.made_for_kids,
            in_playlist=True,
        )

    return source, True


@transaction.atomic
def sync_youtube_roadmap(*, source: YouTubePlaylistRoadmap, preview: PlaylistPreview):
    if source.playlist_id != preview.playlist_id:
        raise ValueError("The fetched playlist does not match this roadmap.")

    section = source.roadmap.sections.order_by("position", "pk").first()
    if section is None:
        section = RoadmapSection.objects.create(
            roadmap=source.roadmap,
            title="Playlist videos",
            slug="playlist-videos",
            position=0,
        )

    existing_by_item_id = {
        video.playlist_item_id: video for video in source.videos.select_related("topic")
    }
    seen_item_ids = set()

    for video in preview.videos:
        seen_item_ids.add(video.playlist_item_id)
        stored = existing_by_item_id.get(video.playlist_item_id)
        if stored is None:
            topic = _create_topic(section=section, video=video) if video.available else None
            YouTubePlaylistVideo.objects.create(
                playlist=source,
                topic=topic,
                playlist_item_id=video.playlist_item_id,
                video_id=video.video_id,
                title=video.title[:300],
                channel_title=video.channel_title[:200],
                thumbnail_url=video.thumbnail_url,
                duration_seconds=video.duration_seconds,
                position=video.position,
                available=video.available,
                embeddable=video.embeddable,
                made_for_kids=video.made_for_kids,
                in_playlist=True,
            )
            continue

        if stored.topic is None and video.available:
            stored.topic = _create_topic(section=section, video=video)
        elif stored.topic is not None:
            stored.topic.title = video.title[:160]
            stored.topic.position = video.position
            stored.topic.description = (
                _topic_description(video)
                if video.available
                else "This video is currently unavailable on YouTube."
            )
            stored.topic.save(update_fields=["title", "position", "description"])

        stored.video_id = video.video_id
        stored.title = video.title[:300]
        stored.channel_title = video.channel_title[:200]
        stored.thumbnail_url = video.thumbnail_url
        stored.duration_seconds = video.duration_seconds
        stored.position = video.position
        stored.available = video.available
        stored.embeddable = video.embeddable
        stored.made_for_kids = video.made_for_kids
        stored.in_playlist = True
        stored.save()

    removed = source.videos.exclude(playlist_item_id__in=seen_item_ids)
    for stored in removed.select_related("topic"):
        stored.in_playlist = False
        stored.available = False
        stored.embeddable = False
        stored.save(
            update_fields=[
                "in_playlist",
                "available",
                "embeddable",
                "updated_at",
            ]
        )
        if stored.topic is not None:
            stored.topic.description = "This video was removed from the source YouTube playlist."
            stored.topic.save(update_fields=["description"])

    source.roadmap.title = preview.title[:140]
    source.roadmap.description = _roadmap_description(preview)
    source.roadmap.source = Roadmap.Source.YOUTUBE
    source.roadmap.save(update_fields=["title", "description", "source", "updated_at"])

    source.source_url = preview.source_url
    source.channel_title = preview.channel_title[:200]
    source.thumbnail_url = preview.thumbnail_url
    source.video_count = preview.video_count
    source.available_video_count = preview.available_video_count
    source.unavailable_video_count = preview.unavailable_video_count
    source.total_duration_seconds = preview.total_duration_seconds
    source.last_synced_at = timezone.now()
    source.save()
    return source
