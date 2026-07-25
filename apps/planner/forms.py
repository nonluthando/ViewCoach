from decimal import Decimal

from django import forms


class StudyPlanPreferencesForm(forms.Form):
    time_budget_hours = forms.DecimalField(
        min_value=Decimal("0.25"),
        max_value=Decimal("16"),
        decimal_places=2,
        max_digits=4,
        label="Hours available today",
        help_text="Enter any amount from 15 minutes to 16 hours, in 15-minute steps.",
        widget=forms.NumberInput(
            attrs={
                "min": "0.25",
                "max": "16",
                "step": "0.25",
                "inputmode": "decimal",
                "placeholder": "e.g. 8",
            }
        ),
    )

    def clean_time_budget_hours(self):
        hours = self.cleaned_data["time_budget_hours"]
        quarter_hours = hours * Decimal("4")
        if quarter_hours != quarter_hours.to_integral_value():
            raise forms.ValidationError("Use 15-minute increments.")
        return hours

    def clean(self):
        cleaned_data = super().clean()
        hours = cleaned_data.get("time_budget_hours")
        if hours is not None:
            cleaned_data["time_budget_minutes"] = int(hours * Decimal("60"))
        return cleaned_data
