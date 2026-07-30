from django.db import models
from django.utils import timezone
from pgvector.django import VectorField


EMBEDDING_DIMENSIONS = 1536


class KnowledgeDocument(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        ARCHIVED = "ARCHIVED", "Archived"

    class Category(models.TextChoices):
        PRODUCT = "PRODUCT", "Product help"
        INTERVIEW_PREP = "INTERVIEW_PREP", "Interview preparation"
        SYSTEM = "SYSTEM", "System guidance"

    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    category = models.CharField(
        max_length=32,
        choices=Category.choices,
        default=Category.PRODUCT,
    )
    summary = models.TextField(blank=True)
    body_markdown = models.TextField()
    source_path = models.CharField(max_length=500, unique=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    content_checksum = models.CharField(max_length=64, blank=True)
    embedding_model = models.CharField(max_length=80, blank=True)
    chunk_count = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    last_ingested_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "title"]
        indexes = [
            models.Index(
                fields=["status", "category"],
                name="knowledge_doc_status_cat_idx",
            ),
        ]

    def publish(self, *, now=None):
        self.status = self.Status.PUBLISHED
        self.published_at = self.published_at or now or timezone.now()

    def __str__(self):
        return self.title


class KnowledgeChunk(models.Model):
    document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    position = models.PositiveIntegerField()
    heading = models.CharField(max_length=300, blank=True)
    content = models.TextField()
    content_checksum = models.CharField(max_length=64)
    character_count = models.PositiveIntegerField()
    token_estimate = models.PositiveIntegerField()
    embedding = VectorField(
        dimensions=EMBEDDING_DIMENSIONS,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["document_id", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "position"],
                name="unique_knowledge_chunk_position",
            ),
        ]
        indexes = [
            models.Index(
                fields=["document", "position"],
                name="knowledge_chunk_doc_pos_idx",
            ),
        ]

    @property
    def citation_label(self):
        if self.heading:
            return f"{self.document.title} — {self.heading}"
        return self.document.title

    def __str__(self):
        return f"{self.document.title} · chunk {self.position}"


class KnowledgeIngestionRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "RUNNING", "Running"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"

    source_label = models.CharField(max_length=500)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.RUNNING,
    )
    documents_seen = models.PositiveIntegerField(default=0)
    documents_ingested = models.PositiveIntegerField(default=0)
    documents_skipped = models.PositiveIntegerField(default=0)
    chunks_created = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at", "-pk"]

    def __str__(self):
        return f"{self.source_label} · {self.status}"
