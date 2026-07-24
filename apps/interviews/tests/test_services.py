from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.interviews.models import MockInterview, MockInterviewItem
from apps.interviews.services import (
    NoInterviewQuestionsError,
    abandon_mock_interview,
    create_mock_interview,
    question_count_for_duration,
    record_mock_interview_response,
    start_mock_interview,
)
from apps.questions.models import (
    BehaviouralQuestion,
    ConceptQuestion,
    DebugQuestion,
    Question,
    TechnicalQuestion,
)
from apps.reviews.models import ReviewAttempt, ReviewState
from apps.reviews.services import record_review

pytestmark = pytest.mark.django_db


def _system_technical(*, key, title):
    return TechnicalQuestion.objects.create(
        is_system=True,
        system_key=key,
        title=title,
        prompt=f"Prompt for {title}",
        difficulty=Question.Difficulty.MEDIUM,
        topic="Algorithms",
        intuition="Explain the reasoning.",
        optimal_approach="Describe the optimal approach.",
    )


def _system_concept(*, key, title):
    return ConceptQuestion.objects.create(
        is_system=True,
        system_key=key,
        title=title,
        prompt=f"Prompt for {title}",
        difficulty=Question.Difficulty.EASY,
        category=ConceptQuestion.Category.BACKEND,
        canonical_answer="A clear canonical answer.",
    )


def _system_behavioural(*, key, title):
    return BehaviouralQuestion.objects.create(
        is_system=True,
        system_key=key,
        title=title,
        prompt=f"Prompt for {title}",
        difficulty=Question.Difficulty.MEDIUM,
        star_answer="Situation, task, action and result.",
    )


def _system_debug(*, key, title):
    return DebugQuestion.objects.create(
        is_system=True,
        system_key=key,
        title=title,
        prompt=f"Prompt for {title}",
        difficulty=Question.Difficulty.MEDIUM,
        likely_bug="The response shape is wrong.",
        fix="Return the expected field.",
    )


def test_question_count_scales_with_duration():
    assert question_count_for_duration(20) == 4
    assert question_count_for_duration(60) == 10


def test_invalid_duration_is_rejected():
    with pytest.raises(ValueError, match="Duration must be one of"):
        question_count_for_duration(25)


def test_mixed_interview_uses_multiple_question_types(user):
    _system_technical(key="tech-1", title="Technical one")
    _system_technical(key="tech-2", title="Technical two")
    _system_concept(key="concept-1", title="Concept one")
    _system_concept(key="concept-2", title="Concept two")
    _system_behavioural(key="behaviour-1", title="Behaviour one")
    _system_debug(key="debug-1", title="Debug one")

    interview = create_mock_interview(
        user=user,
        focus=MockInterview.Focus.MIXED,
        duration_minutes=30,
    )

    question_types = set(interview.items.values_list("question_type", flat=True))
    assert interview.question_count == 6
    assert question_types == {
        Question.Type.TECHNICAL,
        Question.Type.CONCEPT,
        Question.Type.BEHAVIOURAL,
        Question.Type.DEBUG,
    }


def test_focus_limits_the_question_type(user):
    _system_technical(key="tech-focus", title="Technical focus")
    _system_concept(key="concept-focus", title="Concept focus")

    interview = create_mock_interview(
        user=user,
        focus=MockInterview.Focus.CONCEPT,
        duration_minutes=20,
    )

    assert interview.items.count() == 1
    assert interview.items.get().question_type == Question.Type.CONCEPT


def test_user_copy_replaces_the_matching_system_question(user):
    system_question = _system_technical(
        key="copy-source",
        title="Built-in heap question",
    )
    user_copy = TechnicalQuestion.objects.create(
        owner=user,
        source_system_question=system_question,
        title="My heap notes",
        prompt=system_question.prompt,
        difficulty=Question.Difficulty.MEDIUM,
        status=Question.Status.READY_FOR_REVIEW,
        topic="Heaps",
        intuition="My explanation.",
        optimal_approach="Use a priority queue.",
    )

    interview = create_mock_interview(
        user=user,
        focus=MockInterview.Focus.TECHNICAL,
        duration_minutes=20,
    )

    selected_ids = list(interview.items.values_list("question_id", flat=True))
    assert user_copy.pk in selected_ids
    assert system_question.pk not in selected_ids


def test_due_question_receives_priority(user):
    due_question = TechnicalQuestion.objects.create(
        owner=user,
        title="Due question",
        prompt="Explain the due question.",
        status=Question.Status.READY_FOR_REVIEW,
        topic="Queues",
        intuition="Due reasoning.",
    )
    TechnicalQuestion.objects.create(
        owner=user,
        title="Fresh question",
        prompt="Explain the fresh question.",
        status=Question.Status.READY_FOR_REVIEW,
        topic="Arrays",
        intuition="Fresh reasoning.",
    )
    ReviewState.objects.create(
        user=user,
        question=due_question,
        due_at=timezone.now() - timedelta(minutes=5),
    )

    interview = create_mock_interview(
        user=user,
        focus=MockInterview.Focus.TECHNICAL,
        duration_minutes=20,
    )

    assert interview.items.first().question_id == due_question.pk


def test_recent_hard_review_receives_priority(user):
    hard_question = TechnicalQuestion.objects.create(
        owner=user,
        title="Hard question",
        prompt="Explain the hard question.",
        status=Question.Status.READY_FOR_REVIEW,
        topic="Graphs",
        intuition="Hard reasoning.",
    )
    TechnicalQuestion.objects.create(
        owner=user,
        title="Fresh question",
        prompt="Explain the fresh question.",
        status=Question.Status.READY_FOR_REVIEW,
        topic="Arrays",
        intuition="Fresh reasoning.",
    )
    state = ReviewState.objects.create(
        user=user,
        question=hard_question,
        due_at=timezone.now(),
    )
    record_review(
        state=state,
        rating=ReviewAttempt.Rating.HARD,
    )

    interview = create_mock_interview(
        user=user,
        focus=MockInterview.Focus.TECHNICAL,
        duration_minutes=20,
    )

    assert interview.items.first().question_id == hard_question.pk


def test_no_suitable_questions_raises_clear_error(user):
    with pytest.raises(NoInterviewQuestionsError, match="Add or save"):
        create_mock_interview(
            user=user,
            focus=MockInterview.Focus.DEBUG,
            duration_minutes=20,
        )


def test_start_interview_records_start_time(user, technical_question):
    interview = create_mock_interview(
        user=user,
        focus=MockInterview.Focus.TECHNICAL,
        duration_minutes=20,
    )

    start_mock_interview(interview=interview)
    interview.refresh_from_db()

    assert interview.status == MockInterview.Status.IN_PROGRESS
    assert interview.started_at is not None


def test_last_response_completes_interview(user, technical_question):
    interview = create_mock_interview(
        user=user,
        focus=MockInterview.Focus.TECHNICAL,
        duration_minutes=20,
    )
    item = interview.items.get()

    record_mock_interview_response(
        item=item,
        assessment=MockInterviewItem.Assessment.CONFIDENT,
        response_notes="I explained the invariant.",
    )
    interview.refresh_from_db()
    item.refresh_from_db()

    assert interview.status == MockInterview.Status.COMPLETED
    assert interview.completed_at is not None
    assert item.response_notes == "I explained the invariant."


def test_invalid_assessment_does_not_update_item(user, technical_question):
    interview = create_mock_interview(
        user=user,
        focus=MockInterview.Focus.TECHNICAL,
        duration_minutes=20,
    )
    item = interview.items.get()

    with pytest.raises(ValidationError, match="Choose how the answer felt"):
        record_mock_interview_response(
            item=item,
            assessment="UNKNOWN",
        )

    item.refresh_from_db()
    assert item.answered_at is None


def test_abandon_interview_preserves_completed_answers(user, technical_question):
    interview = create_mock_interview(
        user=user,
        focus=MockInterview.Focus.TECHNICAL,
        duration_minutes=20,
    )
    item = interview.items.get()
    item.assessment = MockInterviewItem.Assessment.PARTIAL
    item.answered_at = timezone.now()
    item.save(update_fields=["assessment", "answered_at"])

    abandon_mock_interview(interview=interview)
    interview.refresh_from_db()

    assert interview.status == MockInterview.Status.ABANDONED
    assert interview.answered_count == 1
