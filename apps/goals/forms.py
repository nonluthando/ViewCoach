from django import forms
from django.db import models

from apps.roadmaps.models import Roadmap

from .models import InterviewGoal, InterviewStage


class InterviewGoalForm(forms.ModelForm):
    is_primary = forms.BooleanField(
        required=False,
        label="Make this my primary goal",
    )

    class Meta:
        model = InterviewGoal
        fields = [
            "title",
            "goal_type",
            "role_title",
            "company",
            "roadmap",
            "weekly_minutes",
        ]
        labels = {
            "weekly_minutes": "Weekly study time",
        }
        help_texts = {
            "weekly_minutes": "Total minutes you can realistically study each week.",
            "roadmap": "Optional. The daily plan will prioritise this roadmap.",
        }
        widgets = {
            "weekly_minutes": forms.NumberInput(attrs={"min": 30, "step": 30}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["roadmap"].queryset = Roadmap.objects.filter(
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
