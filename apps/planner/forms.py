from django import forms


class StudyPlanPreferencesForm(forms.Form):
    TIME_BUDGET_CHOICES = (
        (30, "30 minutes"),
        (45, "45 minutes"),
        (60, "1 hour"),
        (90, "1 hour 30 minutes"),
        (120, "2 hours"),
    )

    time_budget_minutes = forms.TypedChoiceField(
        choices=TIME_BUDGET_CHOICES,
        coerce=int,
        label="Time available today",
    )
