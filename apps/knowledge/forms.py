from django import forms


class HelpAssistantForm(forms.Form):
    question = forms.CharField(
        label="What do you need help with?",
        min_length=4,
        max_length=1000,
        help_text=("Ask about ViewCoach features or graduate and junior interview preparation."),
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "placeholder": ("For example: Why did the planner choose this task?"),
                "autocomplete": "off",
            }
        ),
    )

    def clean_question(self):
        return self.cleaned_data["question"].strip()
