from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def backfill_learning_formats(apps, schema_editor):
    Roadmap = apps.get_model("roadmaps", "Roadmap")
    Roadmap.objects.filter(source="YOUTUBE").update(learning_format="VIDEO")
    Roadmap.objects.exclude(source="YOUTUBE").update(learning_format="COURSE")


class Migration(migrations.Migration):
    dependencies = [
        ("roadmaps", "0005_roadmap_focus_and_youtube_groups"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="roadmap",
            name="learning_format",
            field=models.CharField(
                choices=[("COURSE", "Course"), ("VIDEO", "Video")],
                default="COURSE",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="roadmaptopic",
            name="estimated_minutes",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="roadmaptopic",
            name="external_url",
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.CreateModel(
            name="ExternalCourseRoadmap",
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
                (
                    "provider",
                    models.CharField(
                        choices=[
                            ("IBM_SKILLSBUILD", "IBM SkillsBuild"),
                            ("OTHER", "Other provider"),
                        ],
                        max_length=24,
                    ),
                ),
                ("source_url", models.URLField(max_length=500)),
                ("external_key", models.CharField(blank=True, max_length=220)),
                ("language", models.CharField(blank=True, max_length=80)),
                ("thumbnail_url", models.URLField(blank=True, max_length=500)),
                ("total_duration_minutes", models.PositiveIntegerField(default=0)),
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
                        related_name="external_course",
                        to="roadmaps.roadmap",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="external_course_roadmaps",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-updated_at", "-pk"]},
        ),
        migrations.AddConstraint(
            model_name="externalcourseroadmap",
            constraint=models.UniqueConstraint(
                fields=("user", "provider", "source_url"),
                name="unique_user_external_course_url",
            ),
        ),
        migrations.AddIndex(
            model_name="externalcourseroadmap",
            index=models.Index(
                fields=["user", "provider", "-updated_at"],
                name="course_user_provider_idx",
            ),
        ),
        migrations.RunPython(
            backfill_learning_formats,
            migrations.RunPython.noop,
        ),
    ]
