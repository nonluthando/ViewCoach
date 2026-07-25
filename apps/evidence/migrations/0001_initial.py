import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("goals", "0001_initial"),
        ("questions", "0004_seeded_library_models"),
        ("roadmaps", "0002_usertopicresource"),
    ]

    operations = [
        migrations.CreateModel(
            name="EvidenceItem",
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
                    "source_type",
                    models.CharField(
                        choices=[
                            ("PROJECT", "Project"),
                            ("WORK", "Work experience"),
                            ("COURSEWORK", "Coursework"),
                            ("LEADERSHIP", "Leadership or teamwork"),
                            ("INCIDENT", "Technical incident"),
                        ],
                        max_length=16,
                    ),
                ),
                ("title", models.CharField(max_length=180)),
                ("organisation", models.CharField(blank=True, max_length=140)),
                ("role_or_context", models.CharField(blank=True, max_length=180)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("summary", models.TextField(blank=True)),
                ("problem", models.TextField(blank=True)),
                ("personal_contribution", models.TextField(blank=True)),
                ("technologies", models.TextField(blank=True)),
                ("outcomes", models.TextField(blank=True)),
                ("lessons", models.TextField(blank=True)),
                ("evidence_url", models.URLField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evidence_items",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-updated_at", "-created_at", "pk"]},
        ),
        migrations.CreateModel(
            name="BehaviouralStory",
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
                ("title", models.CharField(max_length=180)),
                ("situation", models.TextField()),
                ("task", models.TextField(blank=True)),
                ("actions", models.TextField()),
                ("result", models.TextField(blank=True)),
                ("reflection", models.TextField(blank=True)),
                ("competencies", models.TextField(blank=True)),
                ("follow_up_questions", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "evidence",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="behavioural_stories",
                        to="evidence.evidenceitem",
                    ),
                ),
            ],
            options={"ordering": ["created_at", "pk"]},
        ),
        migrations.CreateModel(
            name="DecisionRecord",
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
                ("title", models.CharField(max_length=180)),
                ("context", models.TextField(blank=True)),
                ("alternatives", models.TextField(blank=True)),
                ("decision", models.TextField()),
                ("rationale", models.TextField(blank=True)),
                ("tradeoffs", models.TextField(blank=True)),
                ("outcome", models.TextField(blank=True)),
                (
                    "would_choose_again",
                    models.CharField(
                        choices=[("YES", "Yes"), ("NO", "No"), ("UNSURE", "Unsure")],
                        default="UNSURE",
                        max_length=8,
                    ),
                ),
                ("reflection", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "evidence",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="decisions",
                        to="evidence.evidenceitem",
                    ),
                ),
            ],
            options={"ordering": ["created_at", "pk"]},
        ),
        migrations.CreateModel(
            name="TopicEvidenceProfile",
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
                    "readiness",
                    models.CharField(
                        choices=[
                            ("KNOWLEDGE_ONLY", "Knowledge only"),
                            ("PROJECT_EVIDENCE", "Project evidence"),
                            ("WORK_EVIDENCE", "Work evidence"),
                            ("INTERVIEW_READY", "Interview ready"),
                        ],
                        default="KNOWLEDGE_ONLY",
                        max_length=20,
                    ),
                ),
                ("personal_angle", models.TextField(blank=True)),
                ("interview_angle", models.TextField(blank=True)),
                ("evidence_gap", models.TextField(blank=True)),
                ("follow_up_questions", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "topic",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evidence_profiles",
                        to="roadmaps.roadmaptopic",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="topic_evidence_profiles",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TopicEvidenceLink",
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
                ("connection_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "evidence",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="topic_links",
                        to="evidence.evidenceitem",
                    ),
                ),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evidence_links",
                        to="evidence.topicevidenceprofile",
                    ),
                ),
            ],
            options={"ordering": ["created_at", "pk"]},
        ),
        migrations.CreateModel(
            name="QuestionEvidenceLink",
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
                ("answer_angle", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "evidence",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="question_links",
                        to="evidence.evidenceitem",
                    ),
                ),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evidence_links",
                        to="questions.question",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="question_evidence_links",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["created_at", "pk"]},
        ),
        migrations.CreateModel(
            name="GoalEvidenceLink",
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
                    "relevance",
                    models.CharField(
                        choices=[("CORE", "Core evidence"), ("SUPPORTING", "Supporting evidence")],
                        default="SUPPORTING",
                        max_length=12,
                    ),
                ),
                ("framing_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "evidence",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="goal_links",
                        to="evidence.evidenceitem",
                    ),
                ),
                (
                    "goal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evidence_links",
                        to="goals.interviewgoal",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="goal_evidence_links",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["relevance", "created_at", "pk"]},
        ),
        migrations.AddIndex(
            model_name="evidenceitem",
            index=models.Index(
                fields=["owner", "source_type", "-updated_at"],
                name="evidence_owner_type_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="topicevidenceprofile",
            constraint=models.UniqueConstraint(
                fields=("user", "topic"),
                name="unique_user_topic_evidence",
            ),
        ),
        migrations.AddIndex(
            model_name="topicevidenceprofile",
            index=models.Index(
                fields=["user", "readiness", "-updated_at"],
                name="topic_evid_user_ready_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="topicevidencelink",
            constraint=models.UniqueConstraint(
                fields=("profile", "evidence"),
                name="unique_topic_evidence_link",
            ),
        ),
        migrations.AddConstraint(
            model_name="questionevidencelink",
            constraint=models.UniqueConstraint(
                fields=("user", "question", "evidence"),
                name="unique_question_evidence_link",
            ),
        ),
        migrations.AddIndex(
            model_name="questionevidencelink",
            index=models.Index(
                fields=["user", "question"],
                name="quest_evid_user_question_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="goalevidencelink",
            constraint=models.UniqueConstraint(
                fields=("user", "goal", "evidence"),
                name="unique_goal_evidence_link",
            ),
        ),
        migrations.AddIndex(
            model_name="goalevidencelink",
            index=models.Index(
                fields=["user", "goal", "relevance"],
                name="goal_evid_user_goal_idx",
            ),
        ),
    ]
