from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.questions.models import Question


class MockInterview(models.Model):
    class Focus(models.TextChoices):
        MIXED = "MIXED", "Mixed interview"
        TECHNICAL = "TECHNICAL", "Technical"
        CONCEPT = "CONCEPT", "Concepts"
        BEHAVIOURAL = "BEHAVIOURAL", "Behavioural"
        DEBUG = "DEBUG", "Repository debugging"

    class Status(models.TextChoices):
        READY = "READY", "Ready"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"
        ABANDONED = "ABANDONED", "Ended early"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mock_interviews",
    )
    goal = models.ForeignKey(
        "goals.InterviewGoal",
        on_delete=models.SET_NULL,
        related_name="mock_interviews",
        null=True,
        blank=True,
    )
    focus = models.CharField(
        max_length=20,
        choices=Focus.choices,
        default=Focus.MIXED,
    )
    duration_minutes = models.PositiveSmallIntegerField(default=30)
    question_count = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.READY,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(
                fields=["user", "status", "-created_at"],
                name="mock_int_user_status_idx",
            )
        ]

    @property
    def answered_count(self):
        return self.items.filter(answered_at__isnull=False).count()

    @property
    def completion_percent(self):
        if self.question_count == 0:
            return 0
        return round((self.answered_count / self.question_count) * 100)

    @property
    def elapsed_minutes(self):
        if self.started_at is None:
            return 0
        end_time = self.completed_at or timezone.now()
        elapsed_seconds = max(0, (end_time - self.started_at).total_seconds())
        return max(1, round(elapsed_seconds / 60))

    @property
    def current_item(self):
        return self.items.filter(answered_at__isnull=True).first()

    @property
    def is_finished(self):
        return self.status in {self.Status.COMPLETED, self.Status.ABANDONED}

    def get_absolute_url(self):
        return reverse("interviews:session", args=[self.pk])

    def __str__(self):
        return f"{self.user} · {self.get_focus_display()} · {self.created_at:%d %b %Y}"


class MockInterviewItem(models.Model):
    class Assessment(models.TextChoices):
        STRUGGLED = "STRUGGLED", "Struggled"
        PARTIAL = "PARTIAL", "Partly confident"
        CONFIDENT = "CONFIDENT", "Confident"
        SKIPPED = "SKIPPED", "Skipped"

    interview = models.ForeignKey(
        MockInterview,
        on_delete=models.CASCADE,
        related_name="items",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.SET_NULL,
        related_name="mock_interview_items",
        null=True,
        blank=True,
    )
    position = models.PositiveSmallIntegerField()
    question_title = models.CharField(max_length=180)
    prompt_snapshot = models.TextField()
    answer_snapshot = models.TextField(blank=True)
    guidance_snapshot = models.TextField(blank=True)
    question_type = models.CharField(max_length=20, choices=Question.Type.choices)
    difficulty = models.CharField(
        max_length=10,
        choices=Question.Difficulty.choices,
        blank=True,
    )
    response_notes = models.TextField(blank=True)
    assessment = models.CharField(
        max_length=16,
        choices=Assessment.choices,
        blank=True,
    )
    answered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["interview", "position"],
                name="unique_mock_interview_position",
            ),
            models.UniqueConstraint(
                fields=["interview", "question"],
                condition=models.Q(question__isnull=False),
                name="unique_mock_interview_question",
            ),
        ]
        indexes = [
            models.Index(
                fields=["interview", "position"],
                name="mock_item_interview_pos_idx",
            )
        ]

    @property
    def is_answered(self):
        return self.answered_at is not None

    @property
    def question_url(self):
        if self.question_id is None:
            return ""
        return reverse("questions:detail", args=[self.question_id])

    def __str__(self):
        return f"{self.interview} · {self.position}. {self.question_title}"
