from pathlib import Path

from django import forms
from django.forms import modelformset_factory

from .models import (
    BehaviouralQuestion,
    ConceptQuestion,
    DebugQuestion,
    Question,
    QuestionImportItem,
    TechnicalQuestion,
    UserQuestionNote,
)

MAX_IMPORT_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_IMPORT_SUFFIXES = {".txt", ".md", ".markdown", ".csv", ".docx", ".pdf"}


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing_classes = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"form-control {existing_classes}".strip()


class TechnicalQuestionForm(StyledModelForm):
    class Meta:
        model = TechnicalQuestion
        fields = [
            "title",
            "prompt",
            "company",
            "difficulty",
            "topic",
            "first_hint",
            "pattern",
            "data_structure",
            "intuition",
            "brute_force",
            "optimal_approach",
            "complexity",
            "mistakes",
            "code",
        ]
        labels = {"prompt": "Prompt"}
        widgets = {
            "prompt": forms.Textarea(attrs={"rows": 7}),
            "first_hint": forms.Textarea(attrs={"rows": 3}),
            "intuition": forms.Textarea(attrs={"rows": 5}),
            "brute_force": forms.Textarea(attrs={"rows": 5}),
            "optimal_approach": forms.Textarea(attrs={"rows": 6}),
            "mistakes": forms.Textarea(attrs={"rows": 4}),
            "code": forms.Textarea(attrs={"rows": 12, "class": "code-input"}),
        }
        help_texts = {
            "prompt": "Write the problem exactly as you want to practise recalling it.",
            "first_hint": "The smallest useful nudge. Do not reveal the full approach.",
            "mistakes": "Record incorrect assumptions, bugs or traps you want to avoid next time.",
        }


class ConceptQuestionForm(StyledModelForm):
    class Meta:
        model = ConceptQuestion
        fields = [
            "title",
            "prompt",
            "category",
            "canonical_answer",
            "example",
            "common_misconception",
            "code_snippet",
        ]
        labels = {
            "prompt": "Question",
            "canonical_answer": "Canonical answer",
            "code_snippet": "Optional code snippet",
        }
        widgets = {
            "prompt": forms.Textarea(attrs={"rows": 5}),
            "canonical_answer": forms.Textarea(attrs={"rows": 10}),
            "example": forms.Textarea(attrs={"rows": 5}),
            "common_misconception": forms.Textarea(attrs={"rows": 5}),
            "code_snippet": forms.Textarea(attrs={"rows": 10, "class": "code-input"}),
        }


class UserQuestionNoteForm(StyledModelForm):
    class Meta:
        model = UserQuestionNote
        fields = ["notes", "mistakes", "code_notes", "behavioural_notes"]
        labels = {
            "notes": "My notes",
            "mistakes": "Mistakes to remember",
            "code_notes": "My code / implementation notes",
            "behavioural_notes": "My story notes",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 8}),
            "mistakes": forms.Textarea(attrs={"rows": 5}),
            "code_notes": forms.Textarea(attrs={"rows": 8, "class": "code-input"}),
            "behavioural_notes": forms.Textarea(attrs={"rows": 8}),
        }


class BehaviouralQuestionForm(StyledModelForm):
    class Meta:
        model = BehaviouralQuestion
        fields = [
            "title",
            "prompt",
            "company",
            "star_answer",
            "leadership_principles",
            "stories",
            "follow_ups",
        ]
        labels = {
            "prompt": "Interview question",
            "leadership_principles": "Competencies / leadership principles",
            "stories": "Supporting story notes",
        }
        widgets = {
            "prompt": forms.Textarea(attrs={"rows": 5}),
            "star_answer": forms.Textarea(attrs={"rows": 10}),
            "leadership_principles": forms.Textarea(attrs={"rows": 3}),
            "stories": forms.Textarea(attrs={"rows": 6}),
            "follow_ups": forms.Textarea(attrs={"rows": 5}),
        }


class DebugQuestionForm(StyledModelForm):
    class Meta:
        model = DebugQuestion
        fields = [
            "title",
            "prompt",
            "company",
            "difficulty",
            "repository",
            "bug_type",
            "broken_code",
            "fix",
            "tests",
        ]
        labels = {
            "prompt": "Debugging scenario",
            "repository": "Repository / project context",
            "tests": "Relevant tests or assertions",
        }
        widgets = {
            "prompt": forms.Textarea(attrs={"rows": 6}),
            "broken_code": forms.Textarea(attrs={"rows": 12, "class": "code-input"}),
            "fix": forms.Textarea(attrs={"rows": 8, "class": "code-input"}),
            "tests": forms.Textarea(attrs={"rows": 8, "class": "code-input"}),
        }
        help_texts = {
            "prompt": "Describe the symptoms and what the code is expected to do.",
            "fix": "Explain the diagnosis and corrected implementation.",
        }


QUESTION_FORM_BY_TYPE = {
    Question.Type.TECHNICAL: TechnicalQuestionForm,
    Question.Type.CONCEPT: ConceptQuestionForm,
    Question.Type.BEHAVIOURAL: BehaviouralQuestionForm,
    Question.Type.DEBUG: DebugQuestionForm,
}


class QuestionImportStartForm(forms.Form):
    default_question_type = forms.ChoiceField(
        choices=Question.Type.choices,
        label="Default question type",
        help_text="You can change individual questions during review.",
    )
    paste_text = forms.CharField(
        required=False,
        label="Paste questions",
        widget=forms.Textarea(
            attrs={
                "rows": 12,
                "placeholder": "1. Explain two sum\n2. Tell me about a conflict\n3. Find the bug…",
            }
        ),
    )
    upload = forms.FileField(
        required=False,
        label="Or upload a file",
        help_text="TXT, Markdown, CSV, DOCX, or a text-based PDF. Maximum 5 MB.",
        widget=forms.ClearableFileInput(attrs={"accept": ".txt,.md,.markdown,.csv,.docx,.pdf"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing_classes = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"form-control {existing_classes}".strip()

    def clean(self):
        cleaned_data = super().clean()
        paste_text = (cleaned_data.get("paste_text") or "").strip()
        upload = cleaned_data.get("upload")

        if bool(paste_text) == bool(upload):
            raise forms.ValidationError("Paste questions or upload one file—not both.")

        cleaned_data["paste_text"] = paste_text
        return cleaned_data

    def clean_upload(self):
        upload = self.cleaned_data.get("upload")
        if upload is None:
            return upload

        suffix = Path(upload.name).suffix.lower()
        if suffix not in ALLOWED_IMPORT_SUFFIXES:
            raise forms.ValidationError("Use a TXT, Markdown, CSV, DOCX, or PDF file.")

        if upload.size > MAX_IMPORT_FILE_SIZE:
            raise forms.ValidationError("The file must be 5 MB or smaller.")

        return upload


class QuestionImportItemForm(StyledModelForm):
    class Meta:
        model = QuestionImportItem
        fields = ["is_included", "generated_title", "question_text", "question_type"]
        labels = {
            "is_included": "Import this question",
            "generated_title": "Title",
            "question_text": "Question",
            "question_type": "Type",
        }
        widgets = {
            "question_text": forms.Textarea(attrs={"rows": 5}),
        }


QuestionImportItemFormSet = modelformset_factory(
    QuestionImportItem,
    form=QuestionImportItemForm,
    extra=0,
)
