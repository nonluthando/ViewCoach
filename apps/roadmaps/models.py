from django.conf import settings
from django.db import models


class Roadmap(models.Model):
    class Kind(models.TextChoices):
        ROLE = "ROLE", "Career roadmap"
        SKILL = "SKILL", "Skill roadmap"
        PRACTICE = "PRACTICE", "Practice roadmap"

    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    position = models.PositiveIntegerField(default=0)
    is_system = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_roadmaps",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "title"]
        indexes = [
            models.Index(fields=["kind", "is_published", "position"], name="roadmap_kind_pub_idx"),
        ]

    def __str__(self) -> str:
        return self.title


class RoadmapSection(models.Model):
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "title"]
        constraints = [
            models.UniqueConstraint(fields=["roadmap", "slug"], name="unique_section_slug"),
        ]
        indexes = [
            models.Index(fields=["roadmap", "position"], name="section_roadmap_pos_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.roadmap}: {self.title}"


class RoadmapTopic(models.Model):
    section = models.ForeignKey(RoadmapSection, on_delete=models.CASCADE, related_name="topics")
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "title"]
        constraints = [
            models.UniqueConstraint(fields=["section", "slug"], name="unique_topic_slug"),
        ]
        indexes = [
            models.Index(fields=["section", "position"], name="topic_section_pos_idx"),
        ]

    @property
    def roadmap(self):
        return self.section.roadmap

    def __str__(self) -> str:
        return f"{self.section}: {self.title}"


class UserRoadmap(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not started"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="roadmap_enrolments",
    )
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name="user_enrolments")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    target_date = models.DateField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "roadmap"], name="unique_user_roadmap"),
        ]
        indexes = [
            models.Index(fields=["user", "status"], name="user_roadmap_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user}: {self.roadmap}"


class UserTopicProgress(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not started"
        IN_PROGRESS = "IN_PROGRESS", "Learning"
        COMPLETED = "COMPLETED", "Completed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="topic_progress",
    )
    topic = models.ForeignKey(RoadmapTopic, on_delete=models.CASCADE, related_name="user_progress")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    notes = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "topic"], name="unique_user_topic_progress"
            ),
        ]
        indexes = [
            models.Index(fields=["user", "status"], name="user_topic_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user}: {self.topic} ({self.get_status_display()})"


class UserTopicResource(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="topic_resources",
    )
    topic = models.ForeignKey(
        RoadmapTopic,
        on_delete=models.CASCADE,
        related_name="user_resources",
    )
    title = models.CharField(max_length=160)
    url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "topic", "url"],
                name="unique_user_topic_resource_url",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user}: {self.topic} — {self.title}"
