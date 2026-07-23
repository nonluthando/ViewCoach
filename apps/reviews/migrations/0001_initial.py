import decimal

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("questions", "0006_question_source_system_question"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReviewState",
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
                    "due_at",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                (
                    "interval_days",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "ease_factor",
                    models.DecimalField(
                        decimal_places=2,
                        default=decimal.Decimal("2.50"),
                        max_digits=4,
                    ),
                ),
                (
                    "repetitions",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "lapses",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "last_reviewed_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="review_states",
                        to="questions.question",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="review_states",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["due_at", "created_at"],
            },
        ),
        migrations.CreateModel(
            name="ReviewAttempt",
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
                    "rating",
                    models.CharField(
                        choices=[
                            ("AGAIN", "Again"),
                            ("HARD", "Hard"),
                            ("GOOD", "Good"),
                            ("EASY", "Easy"),
                        ],
                        max_length=10,
                    ),
                ),
                (
                    "reviewed_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now
                    ),
                ),
                ("previous_due_at", models.DateTimeField()),
                ("scheduled_due_at", models.DateTimeField()),
                (
                    "previous_interval_days",
                    models.PositiveIntegerField(),
                ),
                (
                    "scheduled_interval_days",
                    models.PositiveIntegerField(),
                ),
                (
                    "previous_ease_factor",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=4,
                    ),
                ),
                (
                    "scheduled_ease_factor",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=4,
                    ),
                ),
                (
                    "state",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attempts",
                        to="reviews.reviewstate",
                    ),
                ),
            ],
            options={
                "ordering": ["-reviewed_at", "-pk"],
            },
        ),
        migrations.AddConstraint(
            model_name="reviewstate",
            constraint=models.UniqueConstraint(
                fields=("user", "question"),
                name="unique_user_review_state",
            ),
        ),
        migrations.AddIndex(
            model_name="reviewstate",
            index=models.Index(
                fields=["user", "due_at"],
                name="review_state_user_due_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="reviewattempt",
            index=models.Index(
                fields=["state", "-reviewed_at"],
                name="review_attempt_state_time_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="reviewattempt",
            index=models.Index(
                fields=["rating", "-reviewed_at"],
                name="review_attempt_rating_idx",
            ),
        ),
    ]
