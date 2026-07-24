import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("questions", "0005_expand_debug_repository_context"),
    ]

    operations = [
        migrations.CreateModel(
            name="MockInterview",
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
                    "focus",
                    models.CharField(
                        choices=[
                            ("MIXED", "Mixed interview"),
                            ("TECHNICAL", "Technical"),
                            ("CONCEPT", "Concepts"),
                            ("BEHAVIOURAL", "Behavioural"),
                            ("DEBUG", "Repository debugging"),
                        ],
                        default="MIXED",
                        max_length=20,
                    ),
                ),
                ("duration_minutes", models.PositiveSmallIntegerField(default=30)),
                ("question_count", models.PositiveSmallIntegerField(default=0)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("READY", "Ready"),
                            ("IN_PROGRESS", "In progress"),
                            ("COMPLETED", "Completed"),
                            ("ABANDONED", "Ended early"),
                        ],
                        default="READY",
                        max_length=16,
                    ),
                ),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mock_interviews",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-pk"],
                "indexes": [
                    models.Index(
                        fields=["user", "status", "-created_at"],
                        name="mock_int_user_status_idx",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="MockInterviewItem",
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
                ("position", models.PositiveSmallIntegerField()),
                ("question_title", models.CharField(max_length=180)),
                ("prompt_snapshot", models.TextField()),
                ("answer_snapshot", models.TextField(blank=True)),
                ("guidance_snapshot", models.TextField(blank=True)),
                (
                    "question_type",
                    models.CharField(
                        choices=[
                            ("TECHNICAL", "Technical"),
                            ("CONCEPT", "Concept"),
                            ("BEHAVIOURAL", "Behavioural"),
                            ("DEBUG", "Repository debugging"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "difficulty",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("EASY", "Easy"),
                            ("MEDIUM", "Medium"),
                            ("HARD", "Hard"),
                        ],
                        max_length=10,
                    ),
                ),
                ("response_notes", models.TextField(blank=True)),
                (
                    "assessment",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("STRUGGLED", "Struggled"),
                            ("PARTIAL", "Partly confident"),
                            ("CONFIDENT", "Confident"),
                            ("SKIPPED", "Skipped"),
                        ],
                        max_length=16,
                    ),
                ),
                ("answered_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "interview",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="interviews.mockinterview",
                    ),
                ),
                (
                    "question",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="mock_interview_items",
                        to="questions.question",
                    ),
                ),
            ],
            options={
                "ordering": ["position", "pk"],
                "indexes": [
                    models.Index(
                        fields=["interview", "position"],
                        name="mock_item_interview_pos_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("interview", "position"),
                        name="unique_mock_interview_position",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("question__isnull", False)),
                        fields=("interview", "question"),
                        name="unique_mock_interview_question",
                    ),
                ],
            },
        ),
    ]
