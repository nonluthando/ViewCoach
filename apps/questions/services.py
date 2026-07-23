from copy import deepcopy

from django.db import IntegrityError, transaction

from .models import (
    BehaviouralQuestion,
    ConceptQuestion,
    DebugQuestion,
    Question,
    TechnicalQuestion,
    UserQuestionNote,
    UserQuestionState,
)

COMMON_COPY_FIELDS = (
    "title",
    "prompt",
    "company",
    "difficulty",
)

COPY_FIELDS_BY_TYPE = {
    Question.Type.TECHNICAL: (
        TechnicalQuestion,
        (
            "topic",
            "first_hint",
            "pattern",
            "data_structure",
            "intuition",
            "brute_force",
            "brute_force_time_complexity",
            "brute_force_space_complexity",
            "optimal_approach",
            "optimal_time_complexity",
            "optimal_space_complexity",
            "complexity",
            "mistakes",
            "progressive_hints",
            "code",
        ),
    ),
    Question.Type.CONCEPT: (
        ConceptQuestion,
        (
            "category",
            "canonical_answer",
            "key_points",
            "example",
            "common_misconception",
            "code_snippet",
        ),
    ),
    Question.Type.BEHAVIOURAL: (
        BehaviouralQuestion,
        (
            "star_answer",
            "leadership_principles",
            "stories",
            "follow_ups",
            "competencies",
            "star_outline",
            "personal_detail_prompts",
            "follow_up_questions",
            "common_mistakes",
        ),
    ),
    Question.Type.DEBUG: (
        DebugQuestion,
        (
            "repository",
            "bug_type",
            "failing_test_or_symptom",
            "broken_code",
            "likely_bug",
            "reasoning",
            "fix",
            "tests",
            "common_mistake",
        ),
    ),
}


def _copied_values(source, field_names):
    return {field_name: deepcopy(getattr(source, field_name)) for field_name in field_names}


def _copy_personal_data(*, user, source_question, copied_question):
    source_note = UserQuestionNote.objects.filter(
        user=user,
        question=source_question,
    ).first()
    if source_note is not None:
        UserQuestionNote.objects.update_or_create(
            user=user,
            question=copied_question,
            defaults={
                "notes": source_note.notes,
                "mistakes": source_note.mistakes,
                "code_notes": source_note.code_notes,
                "behavioural_notes": source_note.behavioural_notes,
            },
        )

    source_state = UserQuestionState.objects.filter(
        user=user,
        question=source_question,
    ).first()
    if source_state is not None:
        UserQuestionState.objects.update_or_create(
            user=user,
            question=copied_question,
            defaults={
                "status": source_state.status,
                "bookmarked": False,
                "started_at": source_state.started_at,
                "ready_at": source_state.ready_at,
            },
        )


def copy_built_in_question_for_user(*, question, user):
    if not question.is_system:
        raise ValueError("Only built-in questions can be added to a user library.")

    existing_copy = Question.objects.filter(
        owner=user,
        source_system_question=question,
    ).first()
    if existing_copy is not None:
        _copy_personal_data(
            user=user,
            source_question=question,
            copied_question=existing_copy,
        )
        return existing_copy.specific, False

    source = question.specific
    model_class, type_fields = COPY_FIELDS_BY_TYPE[question.question_type]
    copied_values = _copied_values(source, COMMON_COPY_FIELDS + type_fields)

    try:
        with transaction.atomic():
            copied_question = model_class.objects.create(
                owner=user,
                source_system_question=question,
                is_system=False,
                status=Question.Status.NEEDS_NOTES,
                **copied_values,
            )
            _copy_personal_data(
                user=user,
                source_question=question,
                copied_question=copied_question,
            )
    except IntegrityError:
        copied_question = Question.objects.filter(
            owner=user,
            source_system_question=question,
        ).first()
        if copied_question is None:
            raise

        _copy_personal_data(
            user=user,
            source_question=question,
            copied_question=copied_question,
        )
        return copied_question.specific, False

    if copied_question.can_mark_ready:
        copied_question.mark_ready()

    return copied_question, True
