from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.roadmaps.ibm_client import IBMCoursePreview, IBMOutlineItem
from apps.roadmaps.models import ExternalCourseRoadmap, Roadmap

pytestmark = pytest.mark.django_db


@pytest.fixture
def course_user():
    return User.objects.create_user(
        email="ibm-importer@example.com",
        password="safe-test-password",
    )


@pytest.fixture
def preview():
    return IBMCoursePreview(
        source_url=(
            "https://skillsbuild.org/college-students/course-catalog/"
            "getting-started-with-artificial-intelligence"
        ),
        title="Getting Started with Artificial Intelligence",
        description="Foundational artificial intelligence concepts.",
        duration_minutes=180,
        language="English",
        thumbnail_url="",
        external_key="getting-started-with-artificial-intelligence",
        outline=(
            IBMOutlineItem(
                module_title="Course",
                lesson_title="Artificial intelligence foundations",
                duration_minutes=180,
            ),
        ),
    )


def test_ibm_import_preview_uses_public_metadata(client, course_user, preview):
    client.force_login(course_user)
    with patch(
        "apps.roadmaps.course_views.IBMSkillsBuildClient.fetch_course",
        return_value=preview,
    ):
        response = client.post(
            reverse("roadmaps:ibm_course_import"),
            {"course_url": preview.source_url},
        )
    assert response.status_code == 200
    assert preview.title in response.content.decode()


def test_ibm_import_confirm_creates_owned_course(client, course_user, preview):
    client.force_login(course_user)
    with patch(
        "apps.roadmaps.course_views.IBMSkillsBuildClient.fetch_course",
        return_value=preview,
    ):
        response = client.post(
            reverse("roadmaps:ibm_course_confirm"),
            {
                "source_url": preview.source_url,
                "title": preview.title,
                "description": preview.description,
                "outline_text": (
                    "Course | Artificial intelligence foundations | 180"
                ),
            },
        )
    source = ExternalCourseRoadmap.objects.get(user=course_user)
    assert response.status_code == 302
    assert response.url == reverse(
        "roadmaps:detail",
        kwargs={"slug": source.roadmap.slug},
    )
    assert source.roadmap.created_by == course_user
    assert source.roadmap.source == Roadmap.Source.IBM
