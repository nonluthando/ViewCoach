import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("goals", "0002_goal_roadmaps_and_creation_token"),
    ]

    operations = [
        migrations.AlterField(
            model_name="interviewgoal",
            name="weekly_minutes",
            field=models.PositiveSmallIntegerField(
                default=300,
                validators=[
                    django.core.validators.MinValueValidator(
                        0,
                        message="Weekly study time cannot be negative.",
                    ),
                    django.core.validators.MaxValueValidator(
                        6300,
                        message=(
                            "Weekly study time cannot exceed 6300 minutes "
                            "(105 hours)."
                        ),
                    ),
                ],
            ),
        ),
    ]
