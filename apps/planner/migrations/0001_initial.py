import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("questions", "0005_expand_debug_repository_context"),
        ("roadmaps", "0002_usertopicresource"),
    ]

    operations = [
        migrations.CreateModel(
            name="StudyPlan",
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
                ("plan_date", models.DateField()),
                ("time_budget_minutes", models.PositiveSmallIntegerField(default=60)),
                (
                    "status",
                    models.CharField(
                        choices=[("ACTIVE", "Active"), ("COMPLETED", "Completed")],
                        default="ACTIVE",
                        max_length=12,
                    ),
                ),
                ("generated_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="study_plans",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-plan_date", "-generated_at"],
                "indexes": [
                    models.Index(
                        fields=["user", "-plan_date"],
                        name="study_plan_user_date_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "plan_date"),
                        name="unique_user_daily_study_plan",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="StudySession",
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
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                (
                    "completed_recommendation_count",
                    models.PositiveSmallIntegerField(default=0),
                ),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sessions",
                        to="planner.studyplan",
                    ),
                ),
            ],
            options={
                "ordering": ["-started_at", "-pk"],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("ended_at__isnull", True)),
                        fields=("plan",),
                        name="one_active_session_per_study_plan",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="StudyRecommendation",
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
                    "kind",
                    models.CharField(
                        choices=[
                            ("REVIEW", "Due review"),
                            ("ROADMAP", "Roadmap"),
                            ("WEAK_AREA", "Weak area"),
                            ("PRACTICE", "Practice"),
                            ("LIBRARY", "Question library"),
                        ],
                        max_length=16,
                    ),
                ),
                ("title", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("rationale", models.TextField(blank=True)),
                ("estimated_minutes", models.PositiveSmallIntegerField()),
                ("priority_score", models.PositiveSmallIntegerField(default=0)),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recommendations",
                        to="planner.studyplan",
                    ),
                ),
                (
                    "question",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="study_recommendations",
                        to="questions.question",
                    ),
                ),
                (
                    "topic",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="study_recommendations",
                        to="roadmaps.roadmaptopic",
                    ),
                ),
            ],
            options={
                "ordering": ["position", "-priority_score", "pk"],
                "indexes": [
                    models.Index(
                        fields=["plan", "position"],
                        name="study_rec_plan_pos_idx",
                    )
                ],
            },
        ),
    ]
