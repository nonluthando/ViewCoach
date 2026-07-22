from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("questions", "0004_seeded_library_models"),
    ]

    operations = [
        migrations.AlterField(
            model_name="debugquestion",
            name="repository",
            field=models.TextField(blank=True),
        ),
    ]
