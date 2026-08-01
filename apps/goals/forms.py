from django import forms
from django.db import models

from apps.roadmaps.models import Roadmap

from .models import InterviewGoal, InterviewStage


class InterviewGoalForm(forms.ModelForm):
    is_primary = forms.BooleanField(
        required=False,
        label="Make this my primary goal",
    )
    weekly_minutes = forms.IntegerField(
        min_value=0,
        max_value=6300,
        label="Weekly study time",
        help_text=(
            "Enter your total available study time for the week. Example: 600 minutes = 10 hours."
        ),
        error_messages={
            "invalid": "Enter your weekly study time as a whole number of minutes.",
            "min_value": "Weekly study time cannot be negative.",
            "max_value": "Weekly study time cannot exceed 6300 minutes (105 hours).",
        },
        widget=forms.NumberInput(attrs={"min": 0, "max": 6300, "step": 1, "inputmode": "numeric"}),
    )

    class Meta:
        model = InterviewGoal
        fields = [
            "title",
            "goal_type",
            "role_title",
            "company",
            "roadmaps",
            "weekly_minutes",
        ]
        labels = {
            "roadmaps": "Relevant roadmaps",
        }
        help_texts = {
            "roadmaps": (
                "Select every path that contributes to this goal. The planner will rotate "
                "through the linked roadmaps instead of treating one role as one syllabus."
            ),
        }
        widgets = {
            "roadmaps": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["roadmaps"].queryset = Roadmap.objects.filter(
            is_published=True,
        ).filter(models.Q(is_system=True) | models.Q(created_by=user))
        if not self.is_bound and self.instance.pk:
            self.initial["is_primary"] = self.instance.is_primary


class InterviewStageForm(forms.ModelForm):
    is_current = forms.BooleanField(
        required=False,
        label="This is the next stage",
    )

    class Meta:
        model = InterviewStage
        fields = ["stage_type", "custom_label", "scheduled_for"]
        labels = {
            "scheduled_for": "Date",
        }
        widgets = {
            "scheduled_for": forms.DateInput(attrs={"type": "date"}),
        }
