import pytest

from apps.accounts.models import User
from apps.roadmaps.course_services import (
    create_ibm_course_roadmap,
    parse_course_outline_text,
)
from apps.roadmaps.ibm_client import IBMCoursePreview, IBMOutlineItem
from apps.roadmaps.models import ExternalCourseRoadmap, Roadmap, UserRoadmap

pytestmark = pytest.mark.django_db


def _preview():
    return IBMCoursePreview(
        source_url=(
            "https://skillsbuild.org/college-students/"
            "course-catalog/data-fundamentals"
        ),
        title="Data Fundamentals",
        description="Learn the data ecosystem.",
        duration_minutes=420,
        language="English",
        thumbnail_url="",
        external_key="data-fundamentals",
        outline=(
            IBMOutlineItem(
                module_title="Module 1",
                lesson_title="Understanding data",
                duration_minutes=60,
            ),
        ),
    )


def test_ibm_import_creates_modules_lessons_and_focus():
    user = User.objects.create_user(
        email="course-owner@example.com",
        password="safe-test-password",
    )
    rows = parse_course_outline_text(
        "Module 1 | Understanding data | 60\n"
        "Module 1 | Data tools | 45\n"
        "Assessment | Final assessment | 30"
    )
    source, created = create_ibm_course_roadmap(
        user=user,
        preview=_preview(),
        title="Data Fundamentals",
        description="Learn the data ecosystem.",
        outline_rows=rows,
    )
    assert created is True
    assert source.provider == ExternalCourseRoadmap.Provider.IBM_SKILLSBUILD
    assert source.roadmap.source == Roadmap.Source.IBM
    assert source.roadmap.learning_format == Roadmap.LearningFormat.COURSE
    assert source.roadmap.sections.count() == 2
    assert source.roadmap.sections.first().topics.count() == 2
    assert UserRoadmap.objects.get(
        user=user,
        roadmap=source.roadmap,
    ).is_focused is True
