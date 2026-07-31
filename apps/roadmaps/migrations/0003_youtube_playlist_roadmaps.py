import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("roadmaps", "0002_usertopicresource"),
    ]

    operations = [
        migrations.CreateModel(
            name="YouTubePlaylistRoadmap",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("playlist_id", models.CharField(max_length=100)),
                ("source_url", models.URLField(max_length=500)),
                ("channel_title", models.CharField(blank=True, max_length=200)),
                ("thumbnail_url", models.URLField(blank=True, max_length=500)),
                ("video_count", models.PositiveIntegerField(default=0)),
                (
                    "available_video_count",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "unavailable_video_count",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "total_duration_seconds",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "last_synced_at",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "roadmap",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="youtube_playlist",
                        to="roadmaps.roadmap",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="youtube_playlist_roadmaps",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-pk"],
                "indexes": [
                    models.Index(
                        fields=["user", "last_synced_at"],
                        name="yt_playlist_user_sync_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "playlist_id"),
                        name="unique_user_youtube_playlist",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="YouTubePlaylistVideo",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("playlist_item_id", models.CharField(max_length=120)),
                ("video_id", models.CharField(max_length=100)),
                ("title", models.CharField(max_length=300)),
                ("channel_title", models.CharField(blank=True, max_length=200)),
                ("thumbnail_url", models.URLField(blank=True, max_length=500)),
                ("duration_seconds", models.PositiveIntegerField(default=0)),
                ("position", models.PositiveIntegerField(default=0)),
                ("available", models.BooleanField(default=True)),
                ("embeddable", models.BooleanField(default=True)),
                (
                    "made_for_kids",
                    models.BooleanField(blank=True, null=True),
                ),
                ("in_playlist", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "playlist",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="videos",
                        to="roadmaps.youtubeplaylistroadmap",
                    ),
                ),
                (
                    "topic",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="youtube_video",
                        to="roadmaps.roadmaptopic",
                    ),
                ),
            ],
            options={
                "ordering": ["position", "pk"],
                "indexes": [
                    models.Index(
                        fields=["playlist", "position"],
                        name="yt_video_playlist_pos_idx",
                    ),
                    models.Index(
                        fields=["video_id"],
                        name="yt_video_id_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("playlist", "playlist_item_id"),
                        name="unique_youtube_playlist_item",
                    )
                ],
            },
        ),
    ]
