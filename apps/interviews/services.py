from collections import defaultdict
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.questions.models import Question
from apps.reviews.models import ReviewAttempt, ReviewState

from .forms import DURATION_CHOICES
from .models import MockInterview, MockInterviewItem

QUESTION_COUNT_BY_DURATION = {
    20: 4,
    30: 6,
    45: 8,
    60: 10,
}

MIXED_TYPE_SEQUENCE = (
    Question.Type.TECHNICAL,
    Question.Type.CONCEPT,
    Question.Type.BEHAVIOURAL,
    Question.Type.DEBUG,
    Question.Type.TECHNICAL,
    Question.Type.CONCEPT,
    Question.Type.BEHAVIOURAL,
    Question.Type.TECHNICAL,
    Question.Type.CONCEPT,
    Question.Type.TECHNICAL,
)


class NoInterviewQuestionsError(ValueError):
    pass


def question_count_for_duration(duration_minutes):
    try:
        return QUESTION_COUNT_BY_DURATION[int(duration_minutes)]
    except (KeyError, TypeError, ValueError) as exc:
        valid_durations = ", ".join(str(value) for value, _ in DURATION_CHOICES)
        raise ValueError(f"Duration must be one of: {valid_durations}.") from exc


def _accessible_questions(*, user, focus):
    questions = Question.objects.select_related(
        "technicalquestion",
        "conceptquestion",
        "behaviouralquestion",
        "debugquestion",
    ).filter(
        Q(is_system=True)
        | Q(
            owner=user,
            is_system=False,
            status=Question.Status.READY_FOR_REVIEW,
        )
    )

    copied_source_ids = Question.objects.filter(
        owner=user,
        source_system_question__isnull=False,
        status=Question.Status.READY_FOR_REVIEW,
    ).values_list("source_system_question_id", flat=True)

    questions = questions.exclude(
        is_system=True,
        pk__in=copied_source_ids,
    )

    if focus != MockInterview.Focus.MIXED:
        questions = questions.filter(question_type=focus)

    return list(questions.order_by("pk"))


def _question_priority_scores(*, user, questions, now, goal=None):
    question_ids = [question.pk for question in questions]
    scores = {question_id: 10 for question_id in question_ids}

    for question in questions:
        if question.owner_id == user.pk:
            scores[question.pk] += 6

    due_question_ids = set(
        ReviewState.objects.filter(
            user=user,
            question_id__in=question_ids,
            due_at__lte=now,
        ).values_list("question_id", flat=True)
    )
    for question_id in due_question_ids:
        scores[question_id] += 30

    recent_cutoff = now - timedelta(days=30)
    attempts = (
        ReviewAttempt.objects.filter(
            state__user=user,
            state__question_id__in=question_ids,
            reviewed_at__gte=recent_cutoff,
        )
        .select_related("state")
        .order_by("state__question_id", "-reviewed_at", "-pk")
    )

    latest_rating_by_question = {}
    for attempt in attempts:
        latest_rating_by_question.setdefault(
            attempt.state.question_id,
            attempt.rating,
        )

    rating_bonus = {
        ReviewAttempt.Rating.AGAIN: 45,
        ReviewAttempt.Rating.HARD: 28,
        ReviewAttempt.Rating.GOOD: 6,
        ReviewAttempt.Rating.EASY: 0,
    }
    for question_id, rating in latest_rating_by_question.items():
        scores[question_id] += rating_bonus[rating]

    for question in questions:
        if question.pk not in latest_rating_by_question:
            scores[question.pk] += 8

    if goal is not None:
        keywords = {
            word.lower()
            for word in goal.role_title.replace("/", " ").replace("-", " ").split()
            if len(word) >= 4
        }
        for question in questions:
            searchable = f"{question.title} {question.prompt}".lower()
            if any(keyword in searchable for keyword in keywords):
                scores[question.pk] += 12

    return scores


def _sorted_candidates(*, questions, scores):
    return sorted(
        questions,
        key=lambda question: (
            -scores[question.pk],
            question.question_type,
            question.pk,
        ),
    )


def _select_mixed_questions(*, candidates, count, scores):
    candidates_by_type = defaultdict(list)
    for question in _sorted_candidates(questions=candidates, scores=scores):
        candidates_by_type[question.question_type].append(question)

    selected = []
    selected_ids = set()

    for question_type in MIXED_TYPE_SEQUENCE[:count]:
        bucket = candidates_by_type[question_type]
        while bucket and bucket[0].pk in selected_ids:
            bucket.pop(0)
        if not bucket:
            continue

        question = bucket.pop(0)
        selected.append(question)
        selected_ids.add(question.pk)

    if len(selected) < count:
        for question in _sorted_candidates(questions=candidates, scores=scores):
            if question.pk in selected_ids:
                continue
            selected.append(question)
            selected_ids.add(question.pk)
            if len(selected) == count:
                break

    return selected


def _answer_snapshot(question):
    specific = question.specific
    if specific is question:
        return ""

    if question.question_type == Question.Type.TECHNICAL:
        parts = [
            ("Intuition", specific.intuition),
            ("Optimal approach", specific.optimal_approach),
            ("Brute force", specific.brute_force),
            (
                "Complexity",
                specific.complexity
                or " · ".join(
                    value
                    for value in (
                        specific.optimal_time_complexity,
                        specific.optimal_space_complexity,
                    )
                    if value
                ),
            ),
            ("Reference code", specific.code),
        ]
    elif question.question_type == Question.Type.CONCEPT:
        parts = [
            ("Canonical answer", specific.canonical_answer),
            ("Example", specific.example),
            ("Common misconception", specific.common_misconception),
            ("Code example", specific.code_snippet),
        ]
    elif question.question_type == Question.Type.BEHAVIOURAL:
        parts = [
            ("STAR answer", specific.star_answer),
            ("Stories", specific.stories),
            ("Follow-up preparation", specific.follow_ups),
        ]
    else:
        parts = [
            ("Likely bug", specific.likely_bug),
            ("Reasoning", specific.reasoning),
            ("Fix", specific.fix),
            ("Tests", specific.tests),
        ]

    return "\n\n".join(
        f"{label}\n{value.strip()}"
        for label, value in parts
        if isinstance(value, str) and value.strip()
    )


def _guidance_snapshot(question):
    specific = question.specific
    if specific is question:
        return ""

    if question.question_type == Question.Type.TECHNICAL:
        hints = [specific.first_hint, *specific.progressive_hints]
        return "\n".join(
            f"• {hint.strip()}"
            for hint in hints
            if isinstance(hint, str) and hint.strip()
        )

    if question.question_type == Question.Type.CONCEPT:
        return "\n".join(
            f"• {point.strip()}"
            for point in specific.key_points
            if isinstance(point, str) and point.strip()
        )

    if question.question_type == Question.Type.BEHAVIOURAL:
        prompts = [
            *specific.personal_detail_prompts,
            *specific.follow_up_questions,
        ]
        return "\n".join(
            f"• {prompt.strip()}"
            for prompt in prompts
            if isinstance(prompt, str) and prompt.strip()
        )

    debug_parts = [
        specific.failing_test_or_symptom,
        specific.common_mistake,
    ]
    return "\n".join(
        f"• {part.strip()}"
        for part in debug_parts
        if isinstance(part, str) and part.strip()
    )


def create_mock_interview(*, user, focus, duration_minutes, goal=None, now=None):
    valid_focuses = {value for value, _ in MockInterview.Focus.choices}
    if focus not in valid_focuses:
        raise ValueError("Choose a valid interview focus.")

    if goal is not None and (goal.user_id != user.pk or goal.status != goal.Status.ACTIVE):
        raise ValueError("Choose one of your active interview goals.")

    target_count = question_count_for_duration(duration_minutes)
    current_time = now or timezone.now()
    candidates = _accessible_questions(user=user, focus=focus)
    if not candidates:
        raise NoInterviewQuestionsError(
            "Add or save at least one suitable question before starting a mock interview."
        )

    scores = _question_priority_scores(
        user=user,
        questions=candidates,
        now=current_time,
        goal=goal,
    )

    if focus == MockInterview.Focus.MIXED:
        selected = _select_mixed_questions(
            candidates=candidates,
            count=target_count,
            scores=scores,
        )
    else:
        selected = _sorted_candidates(
            questions=candidates,
            scores=scores,
        )[:target_count]

    with transaction.atomic():
        interview = MockInterview.objects.create(
            user=user,
            focus=focus,
            duration_minutes=duration_minutes,
            question_count=len(selected),
            goal=goal,
        )
        MockInterviewItem.objects.bulk_create(
            [
                MockInterviewItem(
                    interview=interview,
                    question=question,
                    position=position,
                    question_title=question.title,
                    prompt_snapshot=question.prompt,
                    answer_snapshot=_answer_snapshot(question),
                    guidance_snapshot=_guidance_snapshot(question),
                    question_type=question.question_type,
                    difficulty=question.difficulty,
                )
                for position, question in enumerate(selected, start=1)
            ]
        )

    return interview


def start_mock_interview(*, interview, now=None):
    if interview.is_finished:
        return interview

    if interview.status == MockInterview.Status.READY:
        interview.status = MockInterview.Status.IN_PROGRESS
        interview.started_at = now or timezone.now()
        interview.save(
            update_fields=[
                "status",
                "started_at",
                "updated_at",
            ]
        )
    return interview


def record_mock_interview_response(
    *,
    item,
    assessment,
    response_notes="",
    now=None,
):
    valid_assessments = {value for value, _ in MockInterviewItem.Assessment.choices}
    if assessment not in valid_assessments:
        raise ValidationError("Choose how the answer felt.")

    current_time = now or timezone.now()

    with transaction.atomic():
        locked_item = (
            MockInterviewItem.objects.select_for_update()
            .select_related("interview")
            .get(pk=item.pk)
        )
        interview = locked_item.interview

        if interview.is_finished:
            raise ValidationError("This mock interview has already ended.")
        if locked_item.answered_at is not None:
            raise ValidationError("This question has already been recorded.")

        if interview.status == MockInterview.Status.READY:
            interview.status = MockInterview.Status.IN_PROGRESS
            interview.started_at = current_time
            interview.save(
                update_fields=[
                    "status",
                    "started_at",
                    "updated_at",
                ]
            )

        locked_item.response_notes = response_notes.strip()
        locked_item.assessment = assessment
        locked_item.answered_at = current_time
        locked_item.save(
            update_fields=[
                "response_notes",
                "assessment",
                "answered_at",
            ]
        )

        has_remaining_items = interview.items.filter(
            answered_at__isnull=True
        ).exclude(pk=locked_item.pk).exists()

        if not has_remaining_items:
            interview.status = MockInterview.Status.COMPLETED
            interview.completed_at = current_time
            interview.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "updated_at",
                ]
            )

    return interview


def abandon_mock_interview(*, interview, now=None):
    if interview.is_finished:
        return interview

    interview.status = MockInterview.Status.ABANDONED
    interview.completed_at = now or timezone.now()
    interview.save(
        update_fields=[
            "status",
            "completed_at",
            "updated_at",
        ]
    )
    return interview


def mock_interview_summary(*, interview):
    items = list(interview.items.all())
    counts = {
        value: sum(item.assessment == value for item in items)
        for value, _ in MockInterviewItem.Assessment.choices
    }
    answered_items = [item for item in items if item.is_answered]
    weak_items = [
        item
        for item in answered_items
        if item.assessment
        in {
            MockInterviewItem.Assessment.STRUGGLED,
            MockInterviewItem.Assessment.SKIPPED,
        }
    ]

    return {
        "interview": interview,
        "items": items,
        "answered_items": answered_items,
        "weak_items": weak_items,
        "counts": counts,
        "confident_count": counts[MockInterviewItem.Assessment.CONFIDENT],
        "partial_count": counts[MockInterviewItem.Assessment.PARTIAL],
        "struggled_count": counts[MockInterviewItem.Assessment.STRUGGLED],
        "skipped_count": counts[MockInterviewItem.Assessment.SKIPPED],
    }
