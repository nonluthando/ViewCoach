from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.text import slugify

from apps.knowledge.ingestion import ingest_document
from apps.knowledge.models import (
    KnowledgeDocument,
    KnowledgeIngestionRun,
)


CATEGORY_BY_FOLDER = {
    "product": KnowledgeDocument.Category.PRODUCT,
    "interview-prep": KnowledgeDocument.Category.INTERVIEW_PREP,
    "system": KnowledgeDocument.Category.SYSTEM,
}


def _title_from_markdown(markdown, fallback):
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def _summary_from_markdown(markdown):
    paragraphs = []
    for block in markdown.split("\n\n"):
        stripped = block.strip()
        if not stripped or stripped.startswith("#"):
            continue
        paragraphs.append(stripped.replace("\n", " "))
        break
    return paragraphs[0][:500] if paragraphs else ""


class Command(BaseCommand):
    help = (
        "Load trusted Markdown documents, split them into chunks, "
        "and create Gemini embeddings."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default="knowledge_docs",
            help="Directory containing trusted Markdown files.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Rebuild chunks even when the checksum is unchanged.",
        )
        parser.add_argument(
            "--skip-embeddings",
            action="store_true",
            help="Create chunks without calling the embeddings API.",
        )
        parser.add_argument(
            "--draft",
            action="store_true",
            help="Store imported documents as drafts.",
        )
        parser.add_argument(
            "--prune",
            action="store_true",
            help=(
                "Archive database documents from this directory "
                "that no longer exist on disk."
            ),
        )

    def handle(self, *args, **options):
        source_root = Path(options["path"])
        if not source_root.is_absolute():
            source_root = settings.BASE_DIR / source_root
        source_root = source_root.resolve()

        if not source_root.exists() or not source_root.is_dir():
            raise CommandError(
                f"Knowledge directory does not exist: {source_root}"
            )

        markdown_files = sorted(source_root.rglob("*.md"))
        if not markdown_files:
            raise CommandError(
                f"No Markdown files found in {source_root}"
            )

        run = KnowledgeIngestionRun.objects.create(
            source_label=str(source_root),
            documents_seen=len(markdown_files),
        )
        seen_source_paths = set()

        try:
            for file_path in markdown_files:
                markdown = file_path.read_text(encoding="utf-8")
                relative_path = file_path.relative_to(
                    settings.BASE_DIR
                ).as_posix()
                seen_source_paths.add(relative_path)

                folder_name = (
                    file_path.relative_to(source_root).parts[0]
                    if len(file_path.relative_to(source_root).parts) > 1
                    else "product"
                )
                category = CATEGORY_BY_FOLDER.get(
                    folder_name,
                    KnowledgeDocument.Category.PRODUCT,
                )
                fallback_title = file_path.stem.replace("-", " ").title()
                title = _title_from_markdown(
                    markdown,
                    fallback_title,
                )
                slug = slugify(file_path.stem)

                document, _ = (
                    KnowledgeDocument.objects.update_or_create(
                        source_path=relative_path,
                        defaults={
                            "title": title,
                            "slug": slug,
                            "category": category,
                            "summary": _summary_from_markdown(markdown),
                            "body_markdown": markdown,
                            "status": (
                                KnowledgeDocument.Status.DRAFT
                                if options["draft"]
                                else KnowledgeDocument.Status.PUBLISHED
                            ),
                            "published_at": (
                                None
                                if options["draft"]
                                else timezone.now()
                            ),
                        },
                    )
                )

                result = ingest_document(
                    document=document,
                    force=options["force"],
                    create_embeddings=not options[
                        "skip_embeddings"
                    ],
                )
                if result.skipped:
                    run.documents_skipped += 1
                    outcome = "skipped"
                else:
                    run.documents_ingested += 1
                    run.chunks_created += result.chunks_created
                    outcome = (
                        f"{result.chunks_created} chunks"
                    )

                self.stdout.write(
                    f"{relative_path}: {outcome}"
                )

            if options["prune"]:
                KnowledgeDocument.objects.filter(
                    source_path__startswith=(
                        source_root.relative_to(
                            settings.BASE_DIR
                        ).as_posix()
                    ),
                ).exclude(
                    source_path__in=seen_source_paths,
                ).update(
                    status=KnowledgeDocument.Status.ARCHIVED,
                )

            run.status = KnowledgeIngestionRun.Status.SUCCEEDED
            run.finished_at = timezone.now()
            run.save(
                update_fields=[
                    "status",
                    "documents_ingested",
                    "documents_skipped",
                    "chunks_created",
                    "finished_at",
                ]
            )
        except Exception as exc:
            run.status = KnowledgeIngestionRun.Status.FAILED
            run.error_message = str(exc)
            run.finished_at = timezone.now()
            run.save(
                update_fields=[
                    "status",
                    "documents_ingested",
                    "documents_skipped",
                    "chunks_created",
                    "error_message",
                    "finished_at",
                ]
            )
            raise

        self.stdout.write(
            self.style.SUCCESS(
                "Knowledge ingestion complete: "
                f"{run.documents_ingested} ingested, "
                f"{run.documents_skipped} unchanged, "
                f"{run.chunks_created} chunks created."
            )
        )
