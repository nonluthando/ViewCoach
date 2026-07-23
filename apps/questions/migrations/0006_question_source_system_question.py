import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("questions", "0005_expand_debug_repository_context"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="source_system_question",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="user_copies",
                to="questions.question",
            ),
        ),
        migrations.AddIndex(
            model_name="question",
            index=models.Index(
                fields=["owner", "source_system_question"],
                name="question_owner_source_idx",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="question",
            name="question_system_owner_consistency",
        ),
        migrations.AddConstraint(
            model_name="question",
            constraint=models.CheckConstraint(
                condition=(
                    Q(
                        is_system=True,
                        owner__isnull=True,
                        system_key__isnull=False,
                        import_batch__isnull=True,
                        source_system_question__isnull=True,
                    )
                    | Q(
                        is_system=False,
                        owner__isnull=False,
                        system_key__isnull=True,
                    )
                ),
                name="question_system_owner_consistency",
            ),
        ),
        migrations.AddConstraint(
            model_name="question",
            constraint=models.UniqueConstraint(
                condition=Q(source_system_question__isnull=False),
                fields=("owner", "source_system_question"),
                name="unique_user_system_question_copy",
            ),
        ),
    ]
