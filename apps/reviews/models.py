from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.questions.models import Question


class ReviewState(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_states",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="review_states",
    )
    due_at = models.DateTimeField(default=timezone.now)
    interval_days = models.PositiveIntegerField(default=0)
    ease_factor = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("2.50"),
    )
    repetitions = models.PositiveIntegerField(default=0)
    lapses = models.PositiveIntegerField(default=0)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_at", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "question"],
                name="unique_user_review_state",
            )
        ]
        indexes = [
            models.Index(
                fields=["user", "due_at"],
                name="review_state_user_due_idx",
            )
        ]

    def __str__(self):
        return f"{self.user} · {self.question}"


class ReviewAttempt(models.Model):
    class Rating(models.TextChoices):
        AGAIN = "AGAIN", "Again"
        HARD = "HARD", "Hard"
        GOOD = "GOOD", "Good"
        EASY = "EASY", "Easy"

    state = models.ForeignKey(
        ReviewState,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    rating = models.CharField(max_length=10, choices=Rating.choices)
    reviewed_at = models.DateTimeField(default=timezone.now)
    previous_due_at = models.DateTimeField()
    scheduled_due_at = models.DateTimeField()
    previous_interval_days = models.PositiveIntegerField()
    scheduled_interval_days = models.PositiveIntegerField()
    previous_ease_factor = models.DecimalField(max_digits=4, decimal_places=2)
    scheduled_ease_factor = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        ordering = ["-reviewed_at", "-pk"]
        indexes = [
            models.Index(
                fields=["state", "-reviewed_at"],
                name="review_attempt_state_time_idx",
            ),
            models.Index(
                fields=["rating", "-reviewed_at"],
                name="review_attempt_rating_idx",
            ),
        ]

    def __str__(self):
        return f"{self.state.question} · {self.get_rating_display()}"
