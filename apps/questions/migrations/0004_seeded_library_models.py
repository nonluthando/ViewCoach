import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import django.db.models


class Migration(migrations.Migration):
    dependencies = [
        ("questions", "0003_alter_question_status_questionimportbatch_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="question",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="questions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="question",
            name="is_system",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="question",
            name="system_key",
            field=models.SlugField(blank=True, max_length=140, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name="question",
            name="question_type",
            field=models.CharField(
                choices=[
                    ("TECHNICAL", "Technical"),
                    ("CONCEPT", "Concept"),
                    ("BEHAVIOURAL", "Behavioural"),
                    ("DEBUG", "Repository debugging"),
                ],
                editable=False,
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="questionimportbatch",
            name="default_question_type",
            field=models.CharField(
                choices=[
                    ("TECHNICAL", "Technical"),
                    ("CONCEPT", "Concept"),
                    ("BEHAVIOURAL", "Behavioural"),
                    ("DEBUG", "Repository debugging"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="questionimportitem",
            name="question_type",
            field=models.CharField(
                choices=[
                    ("TECHNICAL", "Technical"),
                    ("CONCEPT", "Concept"),
                    ("BEHAVIOURAL", "Behavioural"),
                    ("DEBUG", "Repository debugging"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="technicalquestion",
            name="brute_force_space_complexity",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="technicalquestion",
            name="brute_force_time_complexity",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="technicalquestion",
            name="optimal_space_complexity",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="technicalquestion",
            name="optimal_time_complexity",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="technicalquestion",
            name="progressive_hints",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="behaviouralquestion",
            name="common_mistakes",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="behaviouralquestion",
            name="competencies",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="behaviouralquestion",
            name="follow_up_questions",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="behaviouralquestion",
            name="personal_detail_prompts",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="behaviouralquestion",
            name="star_outline",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="debugquestion",
            name="common_mistake",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="debugquestion",
            name="failing_test_or_symptom",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="debugquestion",
            name="likely_bug",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="debugquestion",
            name="reasoning",
            field=models.TextField(blank=True),
        ),
        migrations.CreateModel(
            name="ConceptQuestion",
            fields=[
                (
                    "question_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="questions.question",
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("JAVA", "Java"),
                            ("PYTHON", "Python"),
                            ("BACKEND", "Backend / CS fundamentals"),
                            ("DATABASES", "Databases"),
                            ("NETWORKING", "Networking"),
                            ("OPERATING_SYSTEMS", "Operating systems"),
                            ("OTHER", "Other"),
                        ],
                        max_length=30,
                    ),
                ),
                ("canonical_answer", models.TextField(blank=True)),
                ("key_points", models.JSONField(blank=True, default=list)),
                ("example", models.TextField(blank=True)),
                ("common_misconception", models.TextField(blank=True)),
                ("code_snippet", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "concept question",
                "verbose_name_plural": "concept questions",
            },
            bases=("questions.question",),
        ),
        migrations.CreateModel(
            name="UserQuestionNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("notes", models.TextField(blank=True)),
                ("mistakes", models.TextField(blank=True)),
                ("code_notes", models.TextField(blank=True)),
                ("behavioural_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "question",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_notes", to="questions.question"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="question_notes", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.CreateModel(
            name="UserQuestionState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("NOT_STARTED", "Not started"),
                            ("IN_PROGRESS", "In progress"),
                            ("READY_FOR_REVIEW", "Ready for review"),
                            ("ARCHIVED", "Archived"),
                        ],
                        default="NOT_STARTED",
                        max_length=20,
                    ),
                ),
                ("bookmarked", models.BooleanField(default=False)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("ready_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "question",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_states", to="questions.question"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="question_states", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="question",
            index=models.Index(fields=["is_system", "question_type"], name="question_system_type_idx"),
        ),
        migrations.AddConstraint(
            model_name="question",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        import_batch__isnull=True,
                        is_system=True,
                        owner__isnull=True,
                        system_key__isnull=False,
                    )
                    | models.Q(
                        is_system=False,
                        owner__isnull=False,
                        system_key__isnull=True,
                    )
                ),
                name="question_system_owner_consistency",
            ),
        ),
        migrations.AddConstraint(
            model_name="userquestionnote",
            constraint=models.UniqueConstraint(fields=("user", "question"), name="unique_user_question_note"),
        ),
        migrations.AddConstraint(
            model_name="userquestionstate",
            constraint=models.UniqueConstraint(fields=("user", "question"), name="unique_user_question_state"),
        ),
        migrations.AddIndex(
            model_name="userquestionstate",
            index=models.Index(fields=["user", "status", "-updated_at"], name="uqstate_user_status_idx"),
        ),
    ]
