import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("goals", "0001_initial"),
        ("interviews", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="mockinterview",
            name="goal",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="mock_interviews",
                to="goals.interviewgoal",
            ),
        ),
    ]
