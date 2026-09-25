from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from apps.knowledge.discovery import discover_form_documents
from apps.knowledge.ingestion import ingest_document
from apps.knowledge.management.commands.ingest_knowledge import _summary_from_markdown
from apps.knowledge.models import KnowledgeDocument, KnowledgeIngestionRun


class Command(BaseCommand):
    help = (
        "Generate SYSTEM knowledge documents from live form definitions "
        "(field labels and help_text) and ingest them, same as ingest_knowledge."
    )

    def add_arguments(self, parser):
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
            help="Store generated documents as drafts.",
        )

    def handle(self, *args, **options):
        documents = discover_form_documents()

        run = KnowledgeIngestionRun.objects.create(
            source_label="generated://forms",
            documents_seen=len(documents),
        )

        try:
            for source_path, title, markdown in documents:
                document, _ = KnowledgeDocument.objects.update_or_create(
                    source_path=source_path,
                    defaults={
                        "title": title,
                        "slug": slugify(title),
                        "category": KnowledgeDocument.Category.SYSTEM,
                        "summary": _summary_from_markdown(markdown),
                        "body_markdown": markdown,
                        "status": (
                            KnowledgeDocument.Status.DRAFT
                            if options["draft"]
                            else KnowledgeDocument.Status.PUBLISHED
                        ),
                        "published_at": (None if options["draft"] else timezone.now()),
                    },
                )

                result = ingest_document(
                    document=document,
                    force=options["force"],
                    create_embeddings=not options["skip_embeddings"],
                )
                if result.skipped:
                    run.documents_skipped += 1
                    outcome = "skipped"
                else:
                    run.documents_ingested += 1
                    run.chunks_created += result.chunks_created
                    outcome = f"{result.chunks_created} chunks"

                self.stdout.write(f"{source_path}: {outcome}")

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
                "System doc discovery complete: "
                f"{run.documents_ingested} ingested, "
                f"{run.documents_skipped} unchanged, "
                f"{run.chunks_created} chunks created."
            )
        )
