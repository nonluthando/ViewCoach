from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("planner", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="studyplan",
            name="selection_best_bound",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="studyplan",
            name="selection_objective",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="studyplan",
            name="selection_solve_time_ms",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="studyplan",
            name="selection_status",
            field=models.CharField(
                choices=[
                    ("OPTIMAL", "Optimal"),
                    ("FEASIBLE", "Feasible"),
                    ("FALLBACK", "Fallback"),
                ],
                default="FALLBACK",
                max_length=16,
            ),
        ),
    ]
