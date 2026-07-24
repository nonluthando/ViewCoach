from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.questions.models import Question
from apps.roadmaps.models import RoadmapTopic


class StudyPlan(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_plans",
    )
    plan_date = models.DateField()
    time_budget_minutes = models.PositiveSmallIntegerField(default=60)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    generated_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-plan_date", "-generated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "plan_date"],
                name="unique_user_daily_study_plan",
            )
        ]
        indexes = [
            models.Index(
                fields=["user", "-plan_date"],
                name="study_plan_user_date_idx",
            )
        ]

    @property
    def estimated_minutes(self):
        return sum(
            recommendation.estimated_minutes
            for recommendation in self.recommendations.all()
        )

    @property
    def completed_count(self):
        return sum(
            recommendation.completed_at is not None
            for recommendation in self.recommendations.all()
        )

    def __str__(self):
        return f"{self.user} · {self.plan_date}"


class StudyRecommendation(models.Model):
    class Kind(models.TextChoices):
        REVIEW = "REVIEW", "Due review"
        ROADMAP = "ROADMAP", "Roadmap"
        WEAK_AREA = "WEAK_AREA", "Weak area"
        PRACTICE = "PRACTICE", "Practice"
        LIBRARY = "LIBRARY", "Question library"

    plan = models.ForeignKey(
        StudyPlan,
        on_delete=models.CASCADE,
        related_name="recommendations",
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    rationale = models.TextField(blank=True)
    estimated_minutes = models.PositiveSmallIntegerField()
    priority_score = models.PositiveSmallIntegerField(default=0)
    position = models.PositiveSmallIntegerField(default=0)
    question = models.ForeignKey(
        Question,
        on_delete=models.SET_NULL,
        related_name="study_recommendations",
        null=True,
        blank=True,
    )
    topic = models.ForeignKey(
        RoadmapTopic,
        on_delete=models.SET_NULL,
        related_name="study_recommendations",
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "-priority_score", "pk"]
        indexes = [
            models.Index(
                fields=["plan", "position"],
                name="study_rec_plan_pos_idx",
            )
        ]

    @property
    def is_completed(self):
        return self.completed_at is not None

    @property
    def action_label(self):
        labels = {
            self.Kind.REVIEW: "Start reviews",
            self.Kind.ROADMAP: "Open topic",
            self.Kind.WEAK_AREA: "Revisit question",
            self.Kind.PRACTICE: "Open practice question",
            self.Kind.LIBRARY: (
                "Open question" if self.question_id else "Open question library"
            ),
        }
        return labels[self.kind]

    @property
    def action_url(self):
        if self.kind == self.Kind.REVIEW:
            if self.question_id:
                return reverse("reviews:review", args=[self.question_id])
            return reverse("reviews:queue")

        if self.topic_id:
            return reverse(
                "roadmaps:topic_detail",
                kwargs={
                    "slug": self.topic.section.roadmap.slug,
                    "topic_id": self.topic_id,
                },
            )

        if self.question_id:
            return reverse("questions:detail", args=[self.question_id])

        return reverse("questions:list")

    def __str__(self):
        return f"{self.plan}: {self.title}"


class StudySession(models.Model):
    plan = models.ForeignKey(
        StudyPlan,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    completed_recommendation_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-started_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan"],
                condition=models.Q(ended_at__isnull=True),
                name="one_active_session_per_study_plan",
            )
        ]

    @property
    def duration_minutes(self):
        end_time = self.ended_at or timezone.now()
        elapsed_seconds = max(0, (end_time - self.started_at).total_seconds())
        return max(1, round(elapsed_seconds / 60))

    def __str__(self):
        return f"Session for {self.plan}"
