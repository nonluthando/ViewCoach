from django import forms

from .course_services import parse_course_outline_text
from .ibm_client import normalize_ibm_course_url


class IBMSkillsBuildImportForm(forms.Form):
    course_url = forms.CharField(
        label="IBM SkillsBuild course",
        max_length=500,
        widget=forms.TextInput(
            attrs={
                "placeholder": "https://skillsbuild.org/.../course-catalog/...",
                "autocomplete": "off",
                "inputmode": "url",
            }
        ),
    )

    def clean_course_url(self):
        value = self.cleaned_data["course_url"].strip()
        try:
            return normalize_ibm_course_url(value)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc


class IBMSkillsBuildConfirmForm(forms.Form):
    source_url = forms.CharField(widget=forms.HiddenInput)
    title = forms.CharField(max_length=140)
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    outline_text = forms.CharField(
        label="Course outline",
        help_text=(
            "One lesson per line: Module | Lesson | minutes. "
            "The minutes column is optional."
        ),
        widget=forms.Textarea(attrs={"rows": 12}),
    )

    def clean_source_url(self):
        value = self.cleaned_data["source_url"].strip()
        try:
            return normalize_ibm_course_url(value)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc

    def clean_outline_text(self):
        value = self.cleaned_data["outline_text"].strip()
        try:
            parse_course_outline_text(value)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc
        return value
