from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from .ibm_client import IBMCoursePreview, IBMOutlineItem
from .models import (
    ExternalCourseRoadmap,
    Roadmap,
    RoadmapSection,
    RoadmapTopic,
    UserRoadmap,
)


@dataclass(frozen=True, slots=True)
class CourseOutlineRow:
    module_title: str
    lesson_title: str
    duration_minutes: int | None


def format_course_outline(items: tuple[IBMOutlineItem, ...]) -> str:
    lines = []
    for item in items:
        duration = str(item.duration_minutes) if item.duration_minutes else ""
        lines.append(
            " | ".join(
                (item.module_title, item.lesson_title, duration)
            ).rstrip(" |")
        )
    return "\n".join(lines)


def parse_course_outline_text(value: str) -> tuple[CourseOutlineRow, ...]:
    rows = []
    for line_number, raw_line in enumerate(value.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) not in {2, 3}:
            raise ValueError(
                f"Line {line_number} must use: Module | Lesson | minutes."
            )
        module_title, lesson_title = parts[:2]
        if not module_title or not lesson_title:
            raise ValueError(
                f"Line {line_number} needs a module and lesson title."
            )
        duration_minutes = None
        if len(parts) == 3 and parts[2]:
            try:
                duration_minutes = int(parts[2])
            except ValueError as exc:
                raise ValueError(
                    f"Line {line_number} has an invalid minute value."
                ) from exc
            if not 1 <= duration_minutes <= 10_000:
                raise ValueError(
                    f"Line {line_number} has an invalid minute value."
                )
        rows.append(
            CourseOutlineRow(
                module_title=module_title[:140],
                lesson_title=lesson_title[:160],
                duration_minutes=duration_minutes,
            )
        )
    if not rows:
        raise ValueError("Add at least one course lesson.")
    if len(rows) > 200:
        raise ValueError("A course import can contain at most 200 lessons.")
    return tuple(rows)


def _unique_slug(user, title):
    base = slugify(title)[:120] or "imported-course"
    root = f"{base}-{user.pk}"
    candidate = root
    suffix = 2
    while Roadmap.objects.filter(slug=candidate).exists():
        candidate = f"{root}-{suffix}"
        suffix += 1
    return candidate[:160]


@transaction.atomic
def create_ibm_course_roadmap(
    *,
    user,
    preview: IBMCoursePreview,
    title: str,
    description: str,
    outline_rows: tuple[CourseOutlineRow, ...],
):
    existing = (
        ExternalCourseRoadmap.objects.filter(
            user=user,
            provider=ExternalCourseRoadmap.Provider.IBM_SKILLSBUILD,
            source_url=preview.source_url,
        )
        .select_related("roadmap")
        .first()
    )
    if existing is not None:
        return existing, False

    roadmap = Roadmap.objects.create(
        title=title.strip()[:140],
        slug=_unique_slug(user, title),
        description=description.strip(),
        kind=Roadmap.Kind.SKILL,
        source=Roadmap.Source.IBM,
        learning_format=Roadmap.LearningFormat.COURSE,
        is_system=False,
        is_published=True,
        created_by=user,
    )
    source = ExternalCourseRoadmap.objects.create(
        user=user,
        roadmap=roadmap,
        provider=ExternalCourseRoadmap.Provider.IBM_SKILLSBUILD,
        source_url=preview.source_url,
        external_key=preview.external_key,
        language=preview.language,
        thumbnail_url=preview.thumbnail_url,
        total_duration_minutes=preview.duration_minutes,
    )

    grouped = OrderedDict()
    for row in outline_rows:
        grouped.setdefault(row.module_title, []).append(row)

    for module_position, (module_title, lessons) in enumerate(
        grouped.items(),
        start=1,
    ):
        section = RoadmapSection.objects.create(
            roadmap=roadmap,
            title=module_title,
            slug=f"{slugify(module_title)[:130] or 'module'}-{module_position}",
            position=module_position,
        )
        for lesson_position, row in enumerate(lessons, start=1):
            RoadmapTopic.objects.create(
                section=section,
                title=row.lesson_title,
                slug=(
                    f"{slugify(row.lesson_title)[:145] or 'lesson'}-"
                    f"{lesson_position}"
                ),
                external_url=preview.source_url,
                estimated_minutes=row.duration_minutes,
                position=lesson_position,
            )

    UserRoadmap.objects.create(
        user=user,
        roadmap=roadmap,
        status=UserRoadmap.Status.IN_PROGRESS,
        is_focused=True,
        started_at=timezone.now(),
    )
    return source, True
