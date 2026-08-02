from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("planner", "0002_studyplan_selection_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="studyrecommendation",
            name="action_path",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="studyrecommendation",
            name="is_required",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="studyrecommendation",
            name="kind",
            field=models.CharField(
                choices=[
                    ("REVIEW", "Due review"),
                    ("STAR", "Daily STAR practice"),
                    ("ROADMAP", "Roadmap"),
                    ("WEAK_AREA", "Weak area"),
                    ("PRACTICE", "Practice"),
                    ("EVIDENCE", "Evidence bank"),
                    ("GUIDE", "Built-in guide"),
                    ("MOCK", "Mock interview"),
                    ("LIBRARY", "Question library"),
                ],
                max_length=16,
            ),
        ),
    ]
