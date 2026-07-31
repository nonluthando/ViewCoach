from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.evaluation import (
    RETRIEVAL_EVALUATION_CASES,
    score_retrieval_case,
)
from apps.knowledge.retrieval import retrieve_knowledge


class Command(BaseCommand):
    help = (
        "Run the deterministic ViewCoach retrieval evaluation set."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--minimum-score",
            type=float,
            default=0.75,
            help="Minimum fraction of cases that must pass.",
        )

    def handle(self, *args, **options):
        minimum_score = options["minimum_score"]
        if minimum_score < 0 or minimum_score > 1:
            raise CommandError(
                "--minimum-score must be between 0 and 1."
            )

        passed = 0
        for case in RETRIEVAL_EVALUATION_CASES:
            results = retrieve_knowledge(
                query=case.question,
                limit=settings.RAG_RETRIEVAL_LIMIT,
            )
            matched, retrieved_slugs = score_retrieval_case(
                case,
                results,
            )
            if matched:
                passed += 1
                outcome = self.style.SUCCESS("PASS")
            else:
                outcome = self.style.ERROR("FAIL")
            self.stdout.write(
                f"{outcome} {case.name}: "
                f"retrieved={list(retrieved_slugs)}"
            )

        total = len(RETRIEVAL_EVALUATION_CASES)
        score = passed / total if total else 0
        self.stdout.write(
            f"Retrieval score: {passed}/{total} ({score:.0%})"
        )
        if score < minimum_score:
            raise CommandError(
                "Retrieval evaluation did not meet the minimum score."
            )
