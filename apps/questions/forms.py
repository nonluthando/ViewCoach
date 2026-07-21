from django import forms

from .models import BehaviouralQuestion, DebugQuestion, Question, TechnicalQuestion


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
            "status",
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


class BehaviouralQuestionForm(StyledModelForm):
    class Meta:
        model = BehaviouralQuestion
        fields = [
            "title",
            "prompt",
            "company",
            "status",
            "star_answer",
            "leadership_principles",
            "stories",
            "follow_ups",
        ]
        labels = {
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
            "status",
            "repository",
            "bug_type",
            "broken_code",
            "fix",
            "tests",
        ]
        labels = {
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
    Question.Type.BEHAVIOURAL: BehaviouralQuestionForm,
    Question.Type.DEBUG: DebugQuestionForm,
}
