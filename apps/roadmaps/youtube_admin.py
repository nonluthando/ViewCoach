from django.contrib import admin

from .models import YouTubePlaylistRoadmap, YouTubePlaylistVideo


class YouTubePlaylistVideoInline(admin.TabularInline):
    model = YouTubePlaylistVideo
    extra = 0
    fields = (
        "position",
        "title",
        "video_id",
        "available",
        "embeddable",
        "in_playlist",
    )
    readonly_fields = fields
    ordering = ("position",)


@admin.register(YouTubePlaylistRoadmap)
class YouTubePlaylistRoadmapAdmin(admin.ModelAdmin):
    list_display = (
        "roadmap",
        "user",
        "playlist_id",
        "available_video_count",
        "last_synced_at",
    )
    list_filter = ("last_synced_at",)
    search_fields = (
        "roadmap__title",
        "user__email",
        "playlist_id",
        "channel_title",
    )
    raw_id_fields = ("user", "roadmap")
    readonly_fields = (
        "playlist_id",
        "source_url",
        "video_count",
        "available_video_count",
        "unavailable_video_count",
        "total_duration_seconds",
        "last_synced_at",
        "created_at",
        "updated_at",
    )
    inlines = (YouTubePlaylistVideoInline,)


@admin.register(YouTubePlaylistVideo)
class YouTubePlaylistVideoAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "playlist",
        "position",
        "available",
        "embeddable",
        "in_playlist",
    )
    list_filter = ("available", "embeddable", "in_playlist")
    search_fields = (
        "title",
        "video_id",
        "playlist__playlist_id",
        "playlist__roadmap__title",
    )
    raw_id_fields = ("playlist", "topic")
