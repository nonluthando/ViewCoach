import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("roadmaps", "0002_usertopicresource"),
    ]

    operations = [
        migrations.CreateModel(
            name="InterviewGoal",
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
                    "goal_type",
                    models.CharField(
                        choices=[
                            ("SPECIFIC_OPPORTUNITY", "Specific opportunity"),
                            ("GENERAL_PREPARATION", "General preparation"),
                        ],
                        max_length=24,
                    ),
                ),
                ("role_title", models.CharField(max_length=140)),
                ("company", models.CharField(blank=True, max_length=140)),
                ("weekly_minutes", models.PositiveSmallIntegerField(default=300)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Active"),
                            ("PAUSED", "Paused"),
                            ("COMPLETED", "Completed"),
                            ("ARCHIVED", "Archived"),
                        ],
                        default="ACTIVE",
                        max_length=12,
                    ),
                ),
                ("is_primary", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "roadmap",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="interview_goals",
                        to="roadmaps.roadmap",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="interview_goals",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-is_primary", "status", "title", "pk"],
            },
        ),
        migrations.CreateModel(
            name="InterviewStage",
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
                    "stage_type",
                    models.CharField(
                        choices=[
                            ("OA", "Online assessment"),
                            ("TECHNICAL", "Technical interview"),
                            ("BEHAVIOURAL", "Behavioural interview"),
                            ("MIXED_FINAL", "Mixed or final interview"),
                            ("CUSTOM", "Custom stage"),
                        ],
                        max_length=16,
                    ),
                ),
                ("custom_label", models.CharField(blank=True, max_length=140)),
                ("scheduled_for", models.DateField(blank=True, null=True)),
                ("is_current", models.BooleanField(default=False)),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "goal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stages",
                        to="goals.interviewgoal",
                    ),
                ),
            ],
            options={
                "ordering": ["position", "scheduled_for", "pk"],
            },
        ),
        migrations.AddConstraint(
            model_name="interviewgoal",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_primary", True), ("status", "ACTIVE")),
                fields=("user",),
                name="one_active_primary_interview_goal",
            ),
        ),
        migrations.AddIndex(
            model_name="interviewgoal",
            index=models.Index(
                fields=["user", "status", "-is_primary"],
                name="goal_user_status_primary_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="interviewstage",
            constraint=models.UniqueConstraint(
                condition=models.Q(("completed_at__isnull", True), ("is_current", True)),
                fields=("goal",),
                name="one_current_stage_per_interview_goal",
            ),
        ),
        migrations.AddIndex(
            model_name="interviewstage",
            index=models.Index(
                fields=["goal", "completed_at", "position"],
                name="stage_goal_complete_pos_idx",
            ),
        ),
    ]
