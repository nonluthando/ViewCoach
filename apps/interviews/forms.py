from django import forms

from .models import MockInterview, MockInterviewItem

DURATION_CHOICES = (
    (20, "20 minutes · 4 questions"),
    (30, "30 minutes · 6 questions"),
    (45, "45 minutes · 8 questions"),
    (60, "60 minutes · 10 questions"),
)


class MockInterviewCreateForm(forms.Form):
    focus = forms.ChoiceField(
        choices=MockInterview.Focus.choices,
        initial=MockInterview.Focus.MIXED,
        help_text="Choose a broad mix or practise one interview format.",
    )
    duration_minutes = forms.TypedChoiceField(
        choices=DURATION_CHOICES,
        coerce=int,
        initial=30,
        help_text="The question count scales with the time available.",
    )


class MockInterviewResponseForm(forms.Form):
    response_notes = forms.CharField(
        required=False,
        label="Your answer notes",
        widget=forms.Textarea(
            attrs={
                "rows": 7,
                "placeholder": (
                    "Capture the structure of your answer, the points you missed, "
                    "or what you would say differently."
                ),
            }
        ),
    )
    assessment = forms.ChoiceField(
        choices=MockInterviewItem.Assessment.choices,
        widget=forms.RadioSelect,
        label="How did that answer feel?",
    )
