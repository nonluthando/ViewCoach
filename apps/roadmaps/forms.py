from django import forms

from .models import UserTopicProgress, UserTopicResource


class TopicNotesForm(forms.ModelForm):
    class Meta:
        model = UserTopicProgress
        fields = ("notes",)
        widgets = {
            "notes": forms.Textarea(
                attrs={
                    "class": "topic-notes-input",
                    "placeholder": (
                        "Capture explanations, examples, mistakes, or anything "
                        "you want to remember."
                    ),
                    "rows": 12,
                }
            )
        }


class TopicQuestionGenerationForm(forms.Form):
    count = forms.TypedChoiceField(
        choices=((3, "3 cards"), (5, "5 cards"), (7, "7 cards")),
        coerce=int,
        initial=5,
        label="Number of draft cards",
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class TopicResourceForm(forms.ModelForm):
    class Meta:
        model = UserTopicResource
        fields = ("title", "url")
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "Resource title",
                    "autocomplete": "off",
                }
            ),
            "url": forms.URLInput(
                attrs={
                    "placeholder": "https://…",
                    "inputmode": "url",
                }
            ),
        }
