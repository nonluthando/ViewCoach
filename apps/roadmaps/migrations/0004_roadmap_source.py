from django.db import migrations, models


def assign_roadmap_sources(apps, schema_editor):
    Roadmap = apps.get_model("roadmaps", "Roadmap")
    YouTubePlaylistRoadmap = apps.get_model(
        "roadmaps",
        "YouTubePlaylistRoadmap",
    )

    youtube_roadmap_ids = YouTubePlaylistRoadmap.objects.values_list(
        "roadmap_id",
        flat=True,
    )
    Roadmap.objects.filter(pk__in=youtube_roadmap_ids).update(
        source="YOUTUBE"
    )
    Roadmap.objects.filter(is_system=True).exclude(
        pk__in=youtube_roadmap_ids
    ).update(source="VIEWCOACH")
    Roadmap.objects.filter(is_system=False).exclude(
        pk__in=youtube_roadmap_ids
    ).update(source="CUSTOM")


class Migration(migrations.Migration):
    dependencies = [
        ("roadmaps", "0003_youtube_playlist_roadmaps"),
    ]

    operations = [
        migrations.AddField(
            model_name="roadmap",
            name="source",
            field=models.CharField(
                choices=[
                    ("VIEWCOACH", "ViewCoach"),
                    ("YOUTUBE", "YouTube"),
                    ("IBM", "IBM SkillsBuild"),
                    ("CUSTOM", "Custom import"),
                ],
                default="VIEWCOACH",
                max_length=20,
            ),
        ),
        migrations.RunPython(
            assign_roadmap_sources,
            migrations.RunPython.noop,
        ),
        migrations.AddIndex(
            model_name="roadmap",
            index=models.Index(
                fields=["source", "is_published", "position"],
                name="roadmap_source_pub_idx",
            ),
        ),
    ]
