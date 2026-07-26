import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("evidence", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectExplanation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "quick_pitch",
                    models.TextField(
                        blank=True,
                        help_text="A concise explanation suitable for a 30-second answer.",
                    ),
                ),
                (
                    "two_minute_answer",
                    models.TextField(
                        blank=True,
                        help_text="The complete interview-ready project explanation.",
                    ),
                ),
                ("architecture", models.TextField(blank=True)),
                ("key_decisions", models.TextField(blank=True)),
                ("difficult_bug", models.TextField(blank=True)),
                ("testing_and_verification", models.TextField(blank=True)),
                ("ai_use", models.TextField(blank=True)),
                ("tradeoffs", models.TextField(blank=True)),
                ("improvements", models.TextField(blank=True)),
                ("scaling", models.TextField(blank=True)),
                ("likely_follow_ups", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "evidence",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="project_explanation",
                        to="evidence.evidenceitem",
                    ),
                ),
            ],
        ),
    ]
