import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.questions.models import (
    BehaviouralQuestion,
    ConceptQuestion,
    DebugQuestion,
    Question,
    TechnicalQuestion,
)

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "core_question_bank.json"
DIFFICULTY = {"beginner": Question.Difficulty.EASY, "intermediate": Question.Difficulty.MEDIUM}
CATEGORY = {
    "java": ConceptQuestion.Category.JAVA,
    "python": ConceptQuestion.Category.PYTHON,
    "backend": ConceptQuestion.Category.BACKEND,
}
BUG_TYPE = {
    "ordering logic": DebugQuestion.BugType.SORTING,
    "response contract violation": DebugQuestion.BugType.API_RESPONSE,
    "date-range boundary and off-by-one error": DebugQuestion.BugType.OFF_BY_ONE,
    "null handling": DebugQuestion.BugType.NULL_HANDLING,
    "incorrect or shared defaults": DebugQuestion.BugType.INCORRECT_DEFAULT,
    "pagination or loop boundary error": DebugQuestion.BugType.OFF_BY_ONE,
    "incorrect dictionary or map key": DebugQuestion.BugType.KEY_TYPO,
}


def _join(values):
    return "\n".join(f"- {value}" for value in values)


class Command(BaseCommand):
    help = "Create or update ViewCoach's built-in starter question library."

    def handle(self, *args, **options):
        try:
            payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Could not read question bank: {exc}") from exc

        required_sections = {
            "technical_questions",
            "concept_questions",
            "debugging_questions",
            "behavioural_questions",
        }
        missing = required_sections - payload.keys()
        if missing:
            raise CommandError(f"Question bank is missing: {', '.join(sorted(missing))}")

        created = 0
        updated = 0
        with transaction.atomic():
            for item in payload["technical_questions"]:
                hints = item["progressive_hints"]
                _, was_created = TechnicalQuestion.objects.update_or_create(
                    system_key=item["system_key"],
                    defaults={
                        "owner": None,
                        "is_system": True,
                        "title": item["title"],
                        "prompt": item["problem_statement"],
                        "difficulty": DIFFICULTY[item["difficulty"]],
                        "status": Question.Status.READY_FOR_REVIEW,
                        "topic": item["topic"],
                        "first_hint": hints[0] if hints else "",
                        "pattern": item["pattern"],
                        "data_structure": hints[2] if len(hints) > 2 else "",
                        "intuition": item["intuition"],
                        "brute_force": item["brute_force_approach"],
                        "brute_force_time_complexity": item["brute_force_time_complexity"],
                        "brute_force_space_complexity": item["brute_force_space_complexity"],
                        "optimal_approach": item["optimal_approach"],
                        "optimal_time_complexity": item["optimal_time_complexity"],
                        "optimal_space_complexity": item["optimal_space_complexity"],
                        "complexity": f"Time: {item['optimal_time_complexity']} Space: {item['optimal_space_complexity']}",
                        "mistakes": _join(item["common_mistakes"]),
                        "progressive_hints": hints,
                        "code": item["java_solution"],
                    },
                )
                created += was_created
                updated += not was_created

            for item in payload["concept_questions"]:
                _, was_created = ConceptQuestion.objects.update_or_create(
                    system_key=item["system_key"],
                    defaults={
                        "owner": None,
                        "is_system": True,
                        "title": item["title"],
                        "prompt": item["question"],
                        "status": Question.Status.READY_FOR_REVIEW,
                        "category": CATEGORY[item["category"]],
                        "canonical_answer": item["canonical_answer"],
                        "key_points": item["key_points"],
                        "example": item["example"],
                        "common_misconception": item["common_misconception"],
                        "code_snippet": item["code_snippet"],
                    },
                )
                created += was_created
                updated += not was_created

            for item in payload["debugging_questions"]:
                _, was_created = DebugQuestion.objects.update_or_create(
                    system_key=item["system_key"],
                    defaults={
                        "owner": None,
                        "is_system": True,
                        "title": item["title"],
                        "prompt": item["scenario"],
                        "status": Question.Status.READY_FOR_REVIEW,
                        "repository": item["repository_context"],
                        "bug_type": BUG_TYPE.get(item["bug_type"], DebugQuestion.BugType.OTHER),
                        "failing_test_or_symptom": item["failing_test_or_symptom"],
                        "likely_bug": item["likely_bug"],
                        "reasoning": item["reasoning"],
                        "fix": item["fix"],
                        "tests": _join(item["tests_to_verify"]),
                        "common_mistake": item["common_mistake"],
                    },
                )
                created += was_created
                updated += not was_created

            for item in payload["behavioural_questions"]:
                principles = item["leadership_principles"]
                _, was_created = BehaviouralQuestion.objects.update_or_create(
                    system_key=item["system_key"],
                    defaults={
                        "owner": None,
                        "is_system": True,
                        "title": item["title"],
                        "prompt": item["question"],
                        "status": Question.Status.READY_FOR_REVIEW,
                        "leadership_principles": _join(principles),
                        "competencies": item["competencies"],
                        "star_outline": item["star_outline"],
                        "personal_detail_prompts": item["prompts_for_personal_details"],
                        "follow_up_questions": item["likely_follow_up_questions"],
                        "common_mistakes": item["common_mistakes"],
                    },
                )
                created += was_created
                updated += not was_created

        total = sum(len(payload[name]) for name in required_sections)
        self.stdout.write(self.style.SUCCESS(f"Seeded {total} built-in questions ({created} created, {updated} updated)."))
