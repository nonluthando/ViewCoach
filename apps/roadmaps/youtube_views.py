from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from apps.evidence.forms import TopicEvidenceLinkForm, TopicEvidenceProfileForm
from apps.evidence.models import EvidenceItem, TopicEvidenceLink, TopicEvidenceProfile

from .forms import TopicNotesForm, TopicResourceForm
from .models import (
    Roadmap,
    UserRoadmap,
    UserTopicProgress,
    UserTopicResource,
    YouTubePlaylistRoadmap,
    YouTubePlaylistVideo,
)
from .services import roadmap_progress, sync_user_roadmap, youtube_roadmap_cards
from .youtube_client import YouTubeDataClient, YouTubeImportError
from .youtube_forms import YouTubePlaylistImportForm
from .youtube_services import create_youtube_roadmap


def _youtube_source_for_user(user, slug, *, with_topics=False):
    sources = YouTubePlaylistRoadmap.objects.filter(
        user=user,
        roadmap__slug=slug,
        roadmap__source=Roadmap.Source.YOUTUBE,
        roadmap__is_published=True,
    ).select_related("roadmap")
    if with_topics:
        sources = sources.prefetch_related("roadmap__sections__topics")
    return get_object_or_404(sources)


def _youtube_video_for_user(user, slug, topic_id):
    source = _youtube_source_for_user(user, slug)
    video = get_object_or_404(
        YouTubePlaylistVideo.objects.select_related(
            "playlist",
            "playlist__roadmap",
            "topic",
            "topic__section",
        ),
        playlist=source,
        topic_id=topic_id,
        topic__isnull=False,
        available=True,
        in_playlist=True,
    )
    return source, video


def _ordered_available_videos(source):
    return list(
        source.videos.filter(
            topic__isnull=False,
            available=True,
            in_playlist=True,
        )
        .select_related("topic")
        .order_by("position", "pk")
    )


@login_required
def youtube_roadmap_list(request):
    return render(
        request,
        "roadmaps/youtube/youtube_roadmap_list.html",
        {"youtube_roadmaps": youtube_roadmap_cards(user=request.user)},
    )


@login_required
def youtube_roadmap_detail(request, slug):
    source = _youtube_source_for_user(
        request.user,
        slug,
        with_topics=True,
    )
    roadmap = source.roadmap
    progress_by_topic = {
        progress.topic_id: progress
        for progress in UserTopicProgress.objects.filter(
            user=request.user,
            topic__section__roadmap=roadmap,
        )
    }

    sections = list(roadmap.sections.all())
    for section in sections:
        section.topic_items = list(section.topics.all())
        for topic in section.topic_items:
            topic.current_progress = progress_by_topic.get(topic.pk)
            topic.current_status = (
                topic.current_progress.status
                if topic.current_progress
                else UserTopicProgress.Status.NOT_STARTED
            )

    videos = _ordered_available_videos(source)
    for video in videos:
        video.topic.current_progress = progress_by_topic.get(video.topic_id)
        video.topic.current_status = (
            video.topic.current_progress.status
            if video.topic.current_progress
            else UserTopicProgress.Status.NOT_STARTED
        )
    video_by_topic = {video.topic_id: video for video in videos}
    for section in sections:
        for topic in section.topic_items:
            topic.youtube_item = video_by_topic.get(topic.pk)

    return render(
        request,
        "roadmaps/youtube/youtube_roadmap_detail.html",
        {
            "source": source,
            "roadmap": roadmap,
            "sections": sections,
            "videos": videos,
            "user_roadmap": UserRoadmap.objects.filter(
                user=request.user,
                roadmap=roadmap,
            ).first(),
            "progress": roadmap_progress(user=request.user, roadmap=roadmap),
        },
    )


@login_required
def youtube_video_detail(request, slug, topic_id):
    source, video = _youtube_video_for_user(
        request.user,
        slug,
        topic_id,
    )
    roadmap = source.roadmap
    topic = video.topic
    progress = UserTopicProgress.objects.filter(
        user=request.user,
        topic=topic,
    ).first()
    ordered_videos = _ordered_available_videos(source)
    current_index = next(index for index, item in enumerate(ordered_videos) if item.pk == video.pk)
    previous_video = ordered_videos[current_index - 1] if current_index > 0 else None
    next_video = (
        ordered_videos[current_index + 1] if current_index + 1 < len(ordered_videos) else None
    )
    evidence_profile = TopicEvidenceProfile.objects.filter(
        user=request.user,
        topic=topic,
    ).first()

    return render(
        request,
        "roadmaps/youtube/youtube_video_workspace.html",
        {
            "source": source,
            "roadmap": roadmap,
            "video": video,
            "topic": topic,
            "progress": progress,
            "current_status": (
                progress.status if progress else UserTopicProgress.Status.NOT_STARTED
            ),
            "video_number": current_index + 1,
            "video_count": len(ordered_videos),
            "previous_video": previous_video,
            "next_video": next_video,
            "notes_form": TopicNotesForm(instance=progress),
            "resource_form": TopicResourceForm(),
            "resources": UserTopicResource.objects.filter(
                user=request.user,
                topic=topic,
            ),
            "evidence_profile": evidence_profile,
            "evidence_profile_form": TopicEvidenceProfileForm(
                instance=evidence_profile,
            ),
            "topic_evidence_links": TopicEvidenceLink.objects.filter(
                profile__user=request.user,
                profile__topic=topic,
            ).select_related("evidence"),
            "topic_evidence_link_form": TopicEvidenceLinkForm(user=request.user),
            "has_evidence_items": EvidenceItem.objects.filter(
                owner=request.user,
            ).exists(),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def youtube_playlist_import(request):
    form = YouTubePlaylistImportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            preview = YouTubeDataClient().fetch_playlist(form.cleaned_data["playlist_url"])
        except YouTubeImportError as exc:
            form.add_error("playlist_url", str(exc))
        else:
            existing = (
                YouTubePlaylistRoadmap.objects.filter(
                    user=request.user,
                    playlist_id=preview.playlist_id,
                )
                .select_related("roadmap")
                .first()
            )
            return render(
                request,
                "roadmaps/youtube_playlist_preview.html",
                {
                    "preview": preview,
                    "playlist_url": form.cleaned_data["playlist_url"],
                    "existing": existing,
                },
            )

    return render(
        request,
        "roadmaps/youtube_playlist_import.html",
        {"form": form},
    )


@login_required
@require_POST
def youtube_playlist_confirm(request):
    form = YouTubePlaylistImportForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Paste a valid YouTube playlist link.")
        return redirect("roadmaps:youtube_import")

    try:
        preview = YouTubeDataClient().fetch_playlist(form.cleaned_data["playlist_url"])
    except YouTubeImportError as exc:
        messages.error(request, str(exc))
        return redirect("roadmaps:youtube_import")

    try:
        source, created = create_youtube_roadmap(
            user=request.user,
            preview=preview,
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("roadmaps:youtube_import")
    if created:
        messages.success(
            request,
            (f"Imported {source.available_video_count} videos into {source.roadmap.title}."),
        )
    else:
        messages.info(
            request,
            "That YouTube playlist is already in your roadmaps.",
        )
    return redirect("roadmaps:youtube_detail", slug=source.roadmap.slug)


@login_required
@require_POST
def complete_youtube_video(request, slug, topic_id):
    source, video = _youtube_video_for_user(
        request.user,
        slug,
        topic_id,
    )
    roadmap = source.roadmap
    topic = video.topic

    now = timezone.now()
    progress, _ = UserTopicProgress.objects.get_or_create(
        user=request.user,
        topic=topic,
    )
    progress.status = UserTopicProgress.Status.COMPLETED
    progress.started_at = progress.started_at or now
    progress.completed_at = now
    progress.save()
    sync_user_roadmap(user=request.user, roadmap=roadmap)

    ordered_videos = _ordered_available_videos(source)
    current_index = next(
        (index for index, item in enumerate(ordered_videos) if item.pk == video.pk),
        None,
    )
    next_video = (
        ordered_videos[current_index + 1]
        if current_index is not None and current_index + 1 < len(ordered_videos)
        else None
    )

    if next_video and next_video.topic:
        messages.success(request, "Marked watched. Moving to the next video.")
        return redirect(
            "roadmaps:youtube_video_detail",
            slug=roadmap.slug,
            topic_id=next_video.topic.pk,
        )

    messages.success(request, "Marked watched. You reached the end of the playlist.")
    return redirect("roadmaps:youtube_detail", slug=roadmap.slug)


@login_required
@require_POST
def delete_youtube_roadmap(request, slug):
    source = get_object_or_404(
        YouTubePlaylistRoadmap.objects.select_related("roadmap"),
        user=request.user,
        roadmap__slug=slug,
        roadmap__source=Roadmap.Source.YOUTUBE,
    )
    title = source.roadmap.title
    source.roadmap.delete()
    messages.success(
        request,
        (f"Removed {title} from ViewCoach. The original YouTube playlist was not changed."),
    )
    return redirect("roadmaps:youtube_list")
