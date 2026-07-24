from datetime import timedelta

import pytest
from django.utils import timezone

from apps.interviews.models import MockInterview, MockInterviewItem
from apps.interviews.services import create_mock_interview

pytestmark = pytest.mark.django_db


def test_interview_progress_uses_answered_items(user, technical_question):
    interview = create_mock_interview(
        user=user,
        focus=MockInterview.Focus.TECHNICAL,
        duration_minutes=20,
    )
    item = interview.items.get()
    item.assessment = MockInterviewItem.Assessment.CONFIDENT
    item.answered_at = timezone.now()
    item.save(update_fields=["assessment", "answered_at"])

    assert interview.answered_count == 1
    assert interview.completion_percent == 100


def test_item_keeps_snapshot_after_question_is_deleted(user, technical_question):
    interview = create_mock_interview(
        user=user,
        focus=MockInterview.Focus.TECHNICAL,
        duration_minutes=20,
    )
    item = interview.items.get()
    title = item.question_title

    technical_question.delete()
    item.refresh_from_db()

    assert item.question is None
    assert item.question_title == title
    assert "min heap" in item.prompt_snapshot


def test_elapsed_minutes_uses_started_and_completed_times(user):
    now = timezone.now()
    interview = MockInterview.objects.create(
        user=user,
        focus=MockInterview.Focus.MIXED,
        duration_minutes=30,
        question_count=0,
        status=MockInterview.Status.COMPLETED,
        started_at=now - timedelta(minutes=12),
        completed_at=now,
    )

    assert interview.elapsed_minutes == 12
