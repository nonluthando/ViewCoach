from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.retrieval import retrieve_knowledge


class Command(BaseCommand):
    help = "Run a semantic search against trusted ViewCoach knowledge."

    def add_arguments(self, parser):
        parser.add_argument("query")
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
        )
        parser.add_argument(
            "--minimum-similarity",
            type=float,
            default=None,
        )

    def handle(self, *args, **options):
        try:
            results = retrieve_knowledge(
                query=options["query"],
                limit=options["limit"],
                minimum_similarity=options[
                    "minimum_similarity"
                ],
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        if not results:
            self.stdout.write(
                self.style.WARNING(
                    "No result met the similarity threshold."
                )
            )
            return

        for index, result in enumerate(results, start=1):
            excerpt = result.content.replace("\n", " ")[:220]
            self.stdout.write(
                (
                    f"{index}. {result.similarity:.3f} · "
                    f"{result.citation_label}\n"
                    f"   {result.source_path}\n"
                    f"   {excerpt}"
                )
            )
