from datetime import date

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.planner.models import StudyPlan, StudyRecommendation

pytestmark = pytest.mark.django_db


def test_user_has_one_study_plan_per_day(user):
    StudyPlan.objects.create(
        user=user,
        plan_date=date(2026, 7, 24),
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        StudyPlan.objects.create(
            user=user,
            plan_date=date(2026, 7, 24),
        )


def test_library_recommendation_without_question_links_to_library(user):
    plan = StudyPlan.objects.create(
        user=user,
        plan_date=date(2026, 7, 24),
    )
    recommendation = StudyRecommendation.objects.create(
        plan=plan,
        kind=StudyRecommendation.Kind.LIBRARY,
        title="Add one interview question",
        estimated_minutes=15,
    )

    assert recommendation.action_url == reverse("questions:list")
    assert recommendation.action_label == "Open question library"
