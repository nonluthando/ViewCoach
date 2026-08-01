from django.conf import settings
from django.db import models
from django.utils import timezone


class Roadmap(models.Model):
    class Kind(models.TextChoices):
        ROLE = "ROLE", "Career roadmap"
        SKILL = "SKILL", "Skill roadmap"
        PRACTICE = "PRACTICE", "Practice roadmap"

    class Source(models.TextChoices):
        VIEWCOACH = "VIEWCOACH", "ViewCoach"
        YOUTUBE = "YOUTUBE", "YouTube"
        IBM = "IBM", "IBM SkillsBuild"
        CUSTOM = "CUSTOM", "Custom import"

    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.VIEWCOACH,
    )
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
            models.Index(
                fields=["source", "is_published", "position"],
                name="roadmap_source_pub_idx",
            ),
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
            models.UniqueConstraint(fields=["user", "topic"], name="unique_user_topic_progress"),
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


class YouTubePlaylistRoadmap(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="youtube_playlist_roadmaps",
    )
    roadmap = models.OneToOneField(
        Roadmap,
        on_delete=models.CASCADE,
        related_name="youtube_playlist",
    )
    playlist_id = models.CharField(max_length=100)
    source_url = models.URLField(max_length=500)
    channel_title = models.CharField(max_length=200, blank=True)
    thumbnail_url = models.URLField(max_length=500, blank=True)
    video_count = models.PositiveIntegerField(default=0)
    available_video_count = models.PositiveIntegerField(default=0)
    unavailable_video_count = models.PositiveIntegerField(default=0)
    total_duration_seconds = models.PositiveIntegerField(default=0)
    last_synced_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "playlist_id"],
                name="unique_user_youtube_playlist",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "last_synced_at"],
                name="yt_playlist_user_sync_idx",
            ),
        ]

    @property
    def total_duration_display(self):
        hours, remainder = divmod(self.total_duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m"
        return f"{seconds}s"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Roadmap.objects.filter(pk=self.roadmap_id).exclude(
            source=Roadmap.Source.YOUTUBE,
        ).update(source=Roadmap.Source.YOUTUBE)

    def __str__(self):
        return f"{self.user}: {self.roadmap.title}"


class YouTubePlaylistVideo(models.Model):
    playlist = models.ForeignKey(
        YouTubePlaylistRoadmap,
        on_delete=models.CASCADE,
        related_name="videos",
    )
    topic = models.OneToOneField(
        RoadmapTopic,
        on_delete=models.SET_NULL,
        related_name="youtube_video",
        null=True,
        blank=True,
    )
    playlist_item_id = models.CharField(max_length=120)
    video_id = models.CharField(max_length=100)
    title = models.CharField(max_length=300)
    channel_title = models.CharField(max_length=200, blank=True)
    thumbnail_url = models.URLField(max_length=500, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    position = models.PositiveIntegerField(default=0)
    available = models.BooleanField(default=True)
    embeddable = models.BooleanField(default=True)
    made_for_kids = models.BooleanField(null=True, blank=True)
    in_playlist = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["playlist", "playlist_item_id"],
                name="unique_youtube_playlist_item",
            ),
        ]
        indexes = [
            models.Index(
                fields=["playlist", "position"],
                name="yt_video_playlist_pos_idx",
            ),
            models.Index(
                fields=["video_id"],
                name="yt_video_id_idx",
            ),
        ]

    @property
    def watch_url(self):
        return f"https://www.youtube.com/watch?v={self.video_id}"

    @property
    def embed_url(self):
        return f"https://www.youtube-nocookie.com/embed/{self.video_id}"

    @property
    def duration_display(self):
        hours, remainder = divmod(self.duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def __str__(self):
        return f"{self.playlist.roadmap.title}: {self.title}"
