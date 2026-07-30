import django.db.models.deletion
import pgvector.django
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        pgvector.django.VectorExtension(),
        migrations.CreateModel(
            name="KnowledgeDocument",
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
                ("title", models.CharField(max_length=180)),
                (
                    "slug",
                    models.SlugField(
                        max_length=180,
                        unique=True,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("PRODUCT", "Product help"),
                            (
                                "INTERVIEW_PREP",
                                "Interview preparation",
                            ),
                            ("SYSTEM", "System guidance"),
                        ],
                        default="PRODUCT",
                        max_length=32,
                    ),
                ),
                ("summary", models.TextField(blank=True)),
                ("body_markdown", models.TextField()),
                (
                    "source_path",
                    models.CharField(
                        max_length=500,
                        unique=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("PUBLISHED", "Published"),
                            ("ARCHIVED", "Archived"),
                        ],
                        default="DRAFT",
                        max_length=16,
                    ),
                ),
                (
                    "content_checksum",
                    models.CharField(
                        blank=True,
                        max_length=64,
                    ),
                ),
                (
                    "embedding_model",
                    models.CharField(
                        blank=True,
                        max_length=80,
                    ),
                ),
                (
                    "chunk_count",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "published_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "last_ingested_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
            ],
            options={
                "ordering": ["category", "title"],
            },
        ),
        migrations.CreateModel(
            name="KnowledgeIngestionRun",
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
                    "source_label",
                    models.CharField(max_length=500),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("RUNNING", "Running"),
                            ("SUCCEEDED", "Succeeded"),
                            ("FAILED", "Failed"),
                        ],
                        default="RUNNING",
                        max_length=16,
                    ),
                ),
                (
                    "documents_seen",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "documents_ingested",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "documents_skipped",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "chunks_created",
                    models.PositiveIntegerField(default=0),
                ),
                ("error_message", models.TextField(blank=True)),
                (
                    "started_at",
                    models.DateTimeField(default=timezone.now),
                ),
                (
                    "finished_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
            ],
            options={
                "ordering": ["-started_at", "-pk"],
            },
        ),
        migrations.CreateModel(
            name="KnowledgeChunk",
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
                ("position", models.PositiveIntegerField()),
                (
                    "heading",
                    models.CharField(
                        blank=True,
                        max_length=300,
                    ),
                ),
                ("content", models.TextField()),
                (
                    "content_checksum",
                    models.CharField(max_length=64),
                ),
                (
                    "character_count",
                    models.PositiveIntegerField(),
                ),
                (
                    "token_estimate",
                    models.PositiveIntegerField(),
                ),
                (
                    "embedding",
                    pgvector.django.VectorField(
                        blank=True,
                        dimensions=1536,
                        null=True,
                    ),
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
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chunks",
                        to="knowledge.knowledgedocument",
                    ),
                ),
            ],
            options={
                "ordering": ["document_id", "position"],
            },
        ),
        migrations.AddIndex(
            model_name="knowledgedocument",
            index=models.Index(
                fields=["status", "category"],
                name="knowledge_doc_status_cat_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="knowledgechunk",
            index=models.Index(
                fields=["document", "position"],
                name="knowledge_chunk_doc_pos_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="knowledgechunk",
            constraint=models.UniqueConstraint(
                fields=("document", "position"),
                name="unique_knowledge_chunk_position",
            ),
        ),
    ]
