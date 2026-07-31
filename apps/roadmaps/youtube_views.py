from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .models import (
    Roadmap,
    RoadmapTopic,
    UserTopicProgress,
    YouTubePlaylistRoadmap,
    YouTubePlaylistVideo,
)
from .services import sync_user_roadmap
from .youtube_client import YouTubeDataClient, YouTubeImportError
from .youtube_forms import YouTubePlaylistImportForm
from .youtube_services import create_youtube_roadmap


@login_required
@require_http_methods(["GET", "POST"])
def youtube_playlist_import(request):
    form = YouTubePlaylistImportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            preview = YouTubeDataClient().fetch_playlist(
                form.cleaned_data["playlist_url"]
            )
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
        preview = YouTubeDataClient().fetch_playlist(
            form.cleaned_data["playlist_url"]
        )
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
            (
                f"Imported {source.available_video_count} videos into "
                f"{source.roadmap.title}."
            ),
        )
    else:
        messages.info(
            request,
            "That YouTube playlist is already in your roadmaps.",
        )
    return redirect("roadmaps:detail", slug=source.roadmap.slug)


@login_required
@require_POST
def complete_youtube_video(request, slug, topic_id):
    roadmap = get_object_or_404(
        Roadmap.objects.filter(
            Q(is_system=True) | Q(created_by=request.user)
        ),
        slug=slug,
        is_published=True,
    )
    topic = get_object_or_404(
        RoadmapTopic.objects.select_related(
            "section",
            "section__roadmap",
        ),
        pk=topic_id,
        section__roadmap=roadmap,
    )
    video = get_object_or_404(
        YouTubePlaylistVideo.objects.select_related("playlist"),
        topic=topic,
        playlist__user=request.user,
    )

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

    ordered_videos = list(
        video.playlist.videos.filter(
            topic__isnull=False,
            available=True,
            in_playlist=True,
        )
        .select_related("topic")
        .order_by("position", "pk")
    )
    current_index = next(
        (
            index
            for index, item in enumerate(ordered_videos)
            if item.pk == video.pk
        ),
        None,
    )
    next_video = (
        ordered_videos[current_index + 1]
        if current_index is not None
        and current_index + 1 < len(ordered_videos)
        else None
    )

    if next_video and next_video.topic:
        messages.success(request, "Marked watched. Moving to the next video.")
        return redirect(
            "roadmaps:topic_detail",
            slug=roadmap.slug,
            topic_id=next_video.topic.pk,
        )

    messages.success(request, "Marked watched. You reached the end of the playlist.")
    return redirect("roadmaps:detail", slug=roadmap.slug)


@login_required
@require_POST
def delete_youtube_roadmap(request, slug):
    source = get_object_or_404(
        YouTubePlaylistRoadmap.objects.select_related("roadmap"),
        user=request.user,
        roadmap__slug=slug,
    )
    title = source.roadmap.title
    source.roadmap.delete()
    messages.success(
        request,
        (
            f"Removed {title} from ViewCoach. "
            "The original YouTube playlist was not changed."
        ),
    )
    return redirect("roadmaps:list")
