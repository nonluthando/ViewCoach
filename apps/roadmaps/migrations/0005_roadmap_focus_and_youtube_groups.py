from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def preserve_current_learning_choices(apps, schema_editor):
    UserRoadmap = apps.get_model("roadmaps", "UserRoadmap")
    YouTubePlaylistRoadmap = apps.get_model("roadmaps", "YouTubePlaylistRoadmap")

    user_ids = (
        UserRoadmap.objects.filter(
            status="IN_PROGRESS",
            roadmap__source="VIEWCOACH",
        )
        .values_list("user_id", flat=True)
        .distinct()
    )
    for user_id in user_ids:
        focused_ids = list(
            UserRoadmap.objects.filter(
                user_id=user_id,
                status="IN_PROGRESS",
                roadmap__source="VIEWCOACH",
            )
            .order_by("started_at", "created_at", "pk")
            .values_list("pk", flat=True)[:4]
        )
        UserRoadmap.objects.filter(pk__in=focused_ids).update(is_focused=True)

    youtube_user_ids = (
        YouTubePlaylistRoadmap.objects.values_list("user_id", flat=True).distinct()
    )
    for user_id in youtube_user_ids:
        favourite_ids = list(
            YouTubePlaylistRoadmap.objects.filter(user_id=user_id)
            .order_by("-updated_at", "-pk")
            .values_list("pk", flat=True)[:5]
        )
        YouTubePlaylistRoadmap.objects.filter(pk__in=favourite_ids).update(
            is_favourite=True
        )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("roadmaps", "0004_roadmap_source"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="YouTubeRoadmapGroup",
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
                ("name", models.CharField(max_length=80)),
                ("position", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="youtube_roadmap_groups",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["position", "name", "pk"],
            },
        ),
        migrations.AddField(
            model_name="userroadmap",
            name="is_focused",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="youtubeplaylistroadmap",
            name="group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="roadmaps",
                to="roadmaps.youtuberoadmapgroup",
            ),
        ),
        migrations.AddField(
            model_name="youtubeplaylistroadmap",
            name="is_favourite",
            field=models.BooleanField(default=False),
        ),
        migrations.AddConstraint(
            model_name="youtuberoadmapgroup",
            constraint=models.UniqueConstraint(
                fields=("user", "name"),
                name="unique_user_youtube_group_name",
            ),
        ),
        migrations.AddIndex(
            model_name="youtuberoadmapgroup",
            index=models.Index(
                fields=["user", "position"],
                name="yt_group_user_position_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="userroadmap",
            index=models.Index(
                fields=["user", "is_focused"],
                name="user_roadmap_focus_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="youtubeplaylistroadmap",
            index=models.Index(
                fields=["user", "is_favourite"],
                name="yt_playlist_user_fav_idx",
            ),
        ),
        migrations.RunPython(
            preserve_current_learning_choices,
            migrations.RunPython.noop,
            atomic=True,
        ),
    ]
