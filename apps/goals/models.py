from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from apps.roadmaps.models import Roadmap


class InterviewGoal(models.Model):
    class GoalType(models.TextChoices):
        SPECIFIC_OPPORTUNITY = "SPECIFIC_OPPORTUNITY", "Specific opportunity"
        GENERAL_PREPARATION = "GENERAL_PREPARATION", "General preparation"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PAUSED = "PAUSED", "Paused"
        COMPLETED = "COMPLETED", "Completed"
        ARCHIVED = "ARCHIVED", "Archived"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interview_goals",
    )
    title = models.CharField(max_length=180)
    goal_type = models.CharField(max_length=24, choices=GoalType.choices)
    role_title = models.CharField(max_length=140)
    company = models.CharField(max_length=140, blank=True)
    roadmaps = models.ManyToManyField(
        Roadmap,
        related_name="interview_goals",
        blank=True,
    )
    weekly_minutes = models.PositiveSmallIntegerField(default=300)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    is_primary = models.BooleanField(default=False)
    creation_token = models.UUIDField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "status", "title", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_primary=True, status="ACTIVE"),
                name="one_active_primary_interview_goal",
            ),
            models.UniqueConstraint(
                fields=["user", "creation_token"],
                condition=models.Q(creation_token__isnull=False),
                name="unique_user_interview_goal_creation_token",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "status", "-is_primary"],
                name="goal_user_status_primary_idx",
            )
        ]

    def clean(self):
        super().clean()
        if self.goal_type == self.GoalType.SPECIFIC_OPPORTUNITY and not self.company.strip():
            raise ValidationError({"company": "Add the company for a specific opportunity."})
        if self.is_primary and self.status != self.Status.ACTIVE:
            raise ValidationError("Only an active goal can be primary.")

    @property
    def current_stage(self):
        current = self.stages.filter(is_current=True, completed_at__isnull=True).first()
        if current is not None:
            return current
        return self.stages.filter(completed_at__isnull=True).order_by(
            "scheduled_for",
            "position",
            "pk",
        ).first()

    @property
    def next_deadline(self):
        stage = self.current_stage
        return stage.scheduled_for if stage else None

    @property
    def weekly_hours(self):
        return round(self.weekly_minutes / 60, 1)

    def get_absolute_url(self):
        return reverse("goals:detail", args=[self.pk])

    def __str__(self):
        return self.title


class InterviewStage(models.Model):
    class StageType(models.TextChoices):
        OA = "OA", "Online assessment"
        TECHNICAL = "TECHNICAL", "Technical interview"
        BEHAVIOURAL = "BEHAVIOURAL", "Behavioural interview"
        MIXED_FINAL = "MIXED_FINAL", "Mixed or final interview"
        CUSTOM = "CUSTOM", "Custom stage"

    goal = models.ForeignKey(
        InterviewGoal,
        on_delete=models.CASCADE,
        related_name="stages",
    )
    stage_type = models.CharField(max_length=16, choices=StageType.choices)
    custom_label = models.CharField(max_length=140, blank=True)
    scheduled_for = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    position = models.PositiveSmallIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "scheduled_for", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["goal"],
                condition=models.Q(is_current=True, completed_at__isnull=True),
                name="one_current_stage_per_interview_goal",
            )
        ]
        indexes = [
            models.Index(
                fields=["goal", "completed_at", "position"],
                name="stage_goal_complete_pos_idx",
            )
        ]

    def clean(self):
        super().clean()
        if self.stage_type == self.StageType.CUSTOM and not self.custom_label.strip():
            raise ValidationError({"custom_label": "Name the custom interview stage."})
        if self.completed_at and self.is_current:
            raise ValidationError("A completed stage cannot remain current.")

    @property
    def display_name(self):
        if self.stage_type == self.StageType.CUSTOM:
            return self.custom_label
        return self.get_stage_type_display()

    def __str__(self):
        return f"{self.goal}: {self.display_name}"
