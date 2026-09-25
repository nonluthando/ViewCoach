from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.answering import GeminiAnswerProvider
from apps.knowledge.evaluation import (
    RETRIEVAL_EVALUATION_CASES,
    score_retrieval_case,
)
from apps.knowledge.judging import FaithfulnessJudgeError, GeminiFaithfulnessJudge
from apps.knowledge.retrieval import build_grounding_context, retrieve_knowledge


class Command(BaseCommand):
    help = "Run the deterministic ViewCoach RAG evaluation set."

    def add_arguments(self, parser):
        parser.add_argument(
            "--minimum-score",
            type=float,
            default=0.75,
            help="Minimum fraction of retrieval cases that must pass (hit@k).",
        )
        parser.add_argument(
            "--minimum-mrr",
            type=float,
            default=0.0,
            help="Minimum mean reciprocal rank required (0 = not enforced).",
        )
        parser.add_argument(
            "--check-faithfulness",
            action="store_true",
            help=(
                "Also generate an answer for each case that retrieved its expected "
                "document and judge it for faithfulness with a second LLM call. "
                "Roughly doubles the API calls made by this command."
            ),
        )
        parser.add_argument(
            "--minimum-faithfulness",
            type=float,
            default=0.8,
            help="Minimum fraction of judged answers that must be faithful.",
        )

    def handle(self, *args, **options):
        minimum_score = options["minimum_score"]
        if not 0 <= minimum_score <= 1:
            raise CommandError("--minimum-score must be between 0 and 1.")
        minimum_mrr = options["minimum_mrr"]
        if not 0 <= minimum_mrr <= 1:
            raise CommandError("--minimum-mrr must be between 0 and 1.")
        minimum_faithfulness = options["minimum_faithfulness"]
        if not 0 <= minimum_faithfulness <= 1:
            raise CommandError("--minimum-faithfulness must be between 0 and 1.")

        answer_provider = GeminiAnswerProvider() if options["check_faithfulness"] else None
        judge = GeminiFaithfulnessJudge() if options["check_faithfulness"] else None

        passed = 0
        reciprocal_ranks = []
        faithfulness_checked = 0
        faithfulness_passed = 0

        for case in RETRIEVAL_EVALUATION_CASES:
            results = retrieve_knowledge(
                query=case.question,
                limit=settings.RAG_RETRIEVAL_LIMIT,
            )
            result = score_retrieval_case(case, results)
            reciprocal_ranks.append(result.reciprocal_rank)

            if result.matched:
                passed += 1
                outcome = self.style.SUCCESS("PASS")
            else:
                outcome = self.style.ERROR("FAIL")
            self.stdout.write(
                f"{outcome} {case.name}: retrieved={list(result.retrieved_slugs)} "
                f"rr={result.reciprocal_rank:.2f}"
            )

            if options["check_faithfulness"] and result.matched:
                faithfulness_checked += 1
                try:
                    generated = answer_provider.generate(
                        question=case.question,
                        context=build_grounding_context(results),
                    )
                    verdict = judge.judge(
                        question=case.question,
                        context=build_grounding_context(results),
                        answer=generated,
                    )
                    if verdict.faithful:
                        faithfulness_passed += 1
                        faith_outcome = self.style.SUCCESS("FAITHFUL")
                    else:
                        faith_outcome = self.style.ERROR("UNFAITHFUL")
                    self.stdout.write(f"    {faith_outcome}: {verdict.reasoning}")
                except FaithfulnessJudgeError as exc:
                    self.stdout.write(self.style.WARNING(f"    JUDGE ERROR: {exc}"))

        total = len(RETRIEVAL_EVALUATION_CASES)
        score = passed / total if total else 0
        mrr = sum(reciprocal_ranks) / total if total else 0
        self.stdout.write(f"Retrieval hit rate: {passed}/{total} ({score:.0%})")
        self.stdout.write(f"Retrieval MRR: {mrr:.3f}")

        if options["check_faithfulness"]:
            faithfulness_score = (
                faithfulness_passed / faithfulness_checked if faithfulness_checked else 0
            )
            self.stdout.write(
                f"Faithfulness: {faithfulness_passed}/{faithfulness_checked} "
                f"({faithfulness_score:.0%})"
            )
            if faithfulness_checked and faithfulness_score < minimum_faithfulness:
                raise CommandError("Faithfulness evaluation did not meet the minimum score.")

        if score < minimum_score:
            raise CommandError("Retrieval evaluation did not meet the minimum hit rate.")
        if minimum_mrr and mrr < minimum_mrr:
            raise CommandError("Retrieval evaluation did not meet the minimum MRR.")
