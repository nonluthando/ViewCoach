import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.roadmaps.models import Roadmap, RoadmapSection, RoadmapTopic

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "core_roadmaps.json"


class Command(BaseCommand):
    help = "Create or update ViewCoach's built-in roadmap catalogue."

    def handle(self, *args, **options):
        try:
            payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Could not read roadmap data: {exc}") from exc

        roadmap_items = payload.get("roadmaps")
        if not isinstance(roadmap_items, list):
            raise CommandError("Roadmap data must contain a roadmaps list.")

        valid_kinds = {value for value, _ in Roadmap.Kind.choices}
        roadmap_created = 0
        roadmap_updated = 0
        section_created = 0
        topic_created = 0

        with transaction.atomic():
            for roadmap_position, item in enumerate(roadmap_items, start=1):
                kind = item.get("kind")
                if kind not in valid_kinds:
                    raise CommandError(f"Unknown roadmap kind: {kind}")

                roadmap, was_created = Roadmap.objects.update_or_create(
                    slug=item["slug"],
                    defaults={
                        "title": item["title"],
                        "description": item.get("description", ""),
                        "kind": kind,
                        "position": item.get("position", roadmap_position),
                        "is_system": True,
                        "is_published": True,
                        "created_by": None,
                    },
                )
                roadmap_created += was_created
                roadmap_updated += not was_created

                for section_position, section_item in enumerate(item["sections"], start=1):
                    section, section_was_created = RoadmapSection.objects.update_or_create(
                        roadmap=roadmap,
                        slug=slugify(section_item["title"]),
                        defaults={
                            "title": section_item["title"],
                            "description": section_item.get("description", ""),
                            "position": section_position,
                        },
                    )
                    section_created += section_was_created

                    for topic_position, topic_item in enumerate(
                        section_item["topics"],
                        start=1,
                    ):
                        if isinstance(topic_item, str):
                            topic_title = topic_item
                            topic_description = ""
                        else:
                            topic_title = topic_item["title"]
                            topic_description = topic_item.get("description", "")

                        _, topic_was_created = RoadmapTopic.objects.update_or_create(
                            section=section,
                            slug=slugify(topic_title),
                            defaults={
                                "title": topic_title,
                                "description": topic_description,
                                "position": topic_position,
                            },
                        )
                        topic_created += topic_was_created

        total_topics = RoadmapTopic.objects.filter(section__roadmap__is_system=True).count()
        self.stdout.write(
            self.style.SUCCESS(
                "Seeded "
                f"{len(roadmap_items)} roadmaps and {total_topics} topics "
                f"({roadmap_created} roadmaps created, {roadmap_updated} updated, "
                f"{section_created} sections created, {topic_created} topics created)."
            )
        )
