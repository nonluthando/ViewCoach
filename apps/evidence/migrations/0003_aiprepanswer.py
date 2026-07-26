import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("evidence", "0002_projectexplanation"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AIPrepAnswer",
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
                ("question_key", models.SlugField(max_length=100)),
                ("answer_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "supporting_evidence",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ai_prep_answers",
                        to="evidence.evidenceitem",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_prep_answers",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["question_key"],
                "indexes": [
                    models.Index(
                        fields=["user", "question_key"],
                        name="ai_prep_user_question_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "question_key"),
                        name="unique_user_ai_prep_answer",
                    )
                ],
            },
        ),
    ]
