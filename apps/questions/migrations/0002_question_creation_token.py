import uuid

from django.db import migrations, models


def populate_creation_tokens(apps, schema_editor):
    Question = apps.get_model("questions", "Question")
    for question in Question.objects.filter(creation_token__isnull=True).iterator():
        question.creation_token = uuid.uuid4()
        question.save(update_fields=["creation_token"])


class Migration(migrations.Migration):
    dependencies = [
        ("questions", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="creation_token",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(populate_creation_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="question",
            name="creation_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
