from django import forms

from .models import Roadmap, RoadmapSection, RoadmapTopic


class CustomRoadmapForm(forms.ModelForm):
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    class Meta:
        model = Roadmap
        fields = ("title", "description", "kind")
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "e.g. Spring Boot interview preparation",
                    "autocomplete": "off",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": (
                        "What this roadmap covers and what you want to achieve."
                    ),
                }
            ),
        }

    def clean_title(self):
        title = " ".join(self.cleaned_data["title"].split())
        duplicates = Roadmap.objects.filter(
            created_by=self.user,
            source=Roadmap.Source.CUSTOM,
            external_course__isnull=True,
            title__iexact=title,
        )
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError(
                "You already have a roadmap with this title."
            )
        return title


class CustomSectionForm(forms.ModelForm):
    def __init__(self, *args, roadmap, **kwargs):
        super().__init__(*args, **kwargs)
        self.roadmap = roadmap

    class Meta:
        model = RoadmapSection
        fields = ("title", "description")
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "e.g. Core framework concepts",
                    "autocomplete": "off",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Optional notes about this module.",
                }
            ),
        }

    def clean_title(self):
        title = " ".join(self.cleaned_data["title"].split())
        duplicates = RoadmapSection.objects.filter(
            roadmap=self.roadmap,
            title__iexact=title,
        )
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError(
                "This roadmap already has a module with that title."
            )
        return title


class CustomTopicForm(forms.ModelForm):
    estimated_minutes = forms.IntegerField(
        required=False,
        min_value=5,
        max_value=1440,
        label="Estimated study time",
        help_text="Optional. Enter the number of minutes.",
        widget=forms.NumberInput(
            attrs={
                "min": 5,
                "max": 1440,
                "step": 5,
                "inputmode": "numeric",
            }
        ),
    )

    def __init__(self, *args, section, **kwargs):
        super().__init__(*args, **kwargs)
        self.section = section

    class Meta:
        model = RoadmapTopic
        fields = (
            "title",
            "description",
            "external_url",
            "estimated_minutes",
        )
        labels = {
            "external_url": "Learning link",
        }
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "e.g. Dependency injection",
                    "autocomplete": "off",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": (
                        "What you need to understand, practise or produce."
                    ),
                }
            ),
            "external_url": forms.URLInput(
                attrs={
                    "placeholder": "https://…",
                    "inputmode": "url",
                }
            ),
        }

    def clean_title(self):
        title = " ".join(self.cleaned_data["title"].split())
        duplicates = RoadmapTopic.objects.filter(
            section=self.section,
            title__iexact=title,
        )
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError(
                "This module already has a topic with that title."
            )
        return title
