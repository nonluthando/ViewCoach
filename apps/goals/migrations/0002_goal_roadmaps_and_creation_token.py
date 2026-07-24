from django.db import migrations, models


def copy_existing_roadmap_links(apps, schema_editor):
    InterviewGoal = apps.get_model("goals", "InterviewGoal")
    through_model = InterviewGoal.roadmaps.through

    for goal in InterviewGoal.objects.exclude(roadmap_id__isnull=True).iterator():
        through_model.objects.get_or_create(
            interviewgoal_id=goal.pk,
            roadmap_id=goal.roadmap_id,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("goals", "0001_initial"),
        ("roadmaps", "0002_usertopicresource"),
    ]

    operations = [
        migrations.AddField(
            model_name="interviewgoal",
            name="roadmaps",
            field=models.ManyToManyField(
                blank=True,
                related_name="+",
                to="roadmaps.roadmap",
            ),
        ),
        migrations.AddField(
            model_name="interviewgoal",
            name="creation_token",
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(
            copy_existing_roadmap_links,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="interviewgoal",
            name="roadmap",
        ),
        migrations.AlterField(
            model_name="interviewgoal",
            name="roadmaps",
            field=models.ManyToManyField(
                blank=True,
                related_name="interview_goals",
                to="roadmaps.roadmap",
            ),
        ),
        migrations.AddConstraint(
            model_name="interviewgoal",
            constraint=models.UniqueConstraint(
                condition=models.Q(("creation_token__isnull", False)),
                fields=("user", "creation_token"),
                name="unique_user_interview_goal_creation_token",
            ),
        ),
    ]
