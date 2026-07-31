from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(
            settings.AUTH_USER_MODEL
        ),
        ("knowledge", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="KnowledgeQueryLog",
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
                ("question", models.TextField()),
                ("answer", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ANSWERED", "Answered"),
                            ("NO_EVIDENCE", "No evidence"),
                            ("ERROR", "Error"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "generation_model",
                    models.CharField(
                        blank=True,
                        max_length=100,
                    ),
                ),
                (
                    "retrieved_chunk_ids",
                    models.JSONField(
                        blank=True,
                        default=list,
                    ),
                ),
                (
                    "citations",
                    models.JSONField(
                        blank=True,
                        default=list,
                    ),
                ),
                (
                    "top_similarity",
                    models.FloatField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "latency_ms",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "error_message",
                    models.TextField(blank=True),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=(
                            django.db.models.deletion.SET_NULL
                        ),
                        related_name="knowledge_query_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-pk"],
                "indexes": [
                    models.Index(
                        fields=["status", "created_at"],
                        name="know_q_status_created_idx",
                    ),
                    models.Index(
                        fields=["user", "created_at"],
                        name="know_q_user_created_idx",
                    ),
                ],
            },
        ),
    ]
