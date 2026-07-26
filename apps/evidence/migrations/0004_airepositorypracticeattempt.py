import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("evidence", "0003_aiprepanswer"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AIRepositoryPracticeAttempt",
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
                ("title", models.CharField(max_length=180)),
                (
                    "scenario_type",
                    models.CharField(
                        choices=[
                            ("DEBUGGING", "Debugging failures"),
                            ("FEATURE", "Small feature"),
                            ("MIXED", "Debugging and feature"),
                        ],
                        default="MIXED",
                        max_length=12,
                    ),
                ),
                ("practiced_on", models.DateField(default=django.utils.timezone.localdate)),
                ("duration_minutes", models.PositiveSmallIntegerField(default=60)),
                ("tests_fixed", models.PositiveSmallIntegerField(default=0)),
                ("feature_completed", models.BooleanField(default=False)),
                ("full_suite_passed", models.BooleanField(default=False)),
                ("ai_use_note", models.TextField(blank=True)),
                ("reflection", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_repository_practice_attempts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-practiced_on", "-created_at"],
                "indexes": [
                    models.Index(
                        fields=["user", "-practiced_on"],
                        name="ai_repo_user_practice_idx",
                    )
                ],
            },
        ),
    ]
