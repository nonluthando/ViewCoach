from django import forms

from .models import (
    BehaviouralStory,
    DecisionRecord,
    EvidenceItem,
    GoalEvidenceLink,
    ProjectExplanation,
    QuestionEvidenceLink,
    TopicEvidenceLink,
    TopicEvidenceProfile,
)


class EvidenceItemForm(forms.ModelForm):
    class Meta:
        model = EvidenceItem
        fields = [
            "source_type",
            "title",
            "organisation",
            "role_or_context",
            "start_date",
            "end_date",
            "summary",
            "problem",
            "personal_contribution",
            "technologies",
            "outcomes",
            "lessons",
            "evidence_url",
        ]
        labels = {
            "role_or_context": "Role or context",
            "personal_contribution": "What I personally did",
            "technologies": "Technologies and skills",
            "outcomes": "Outcome or impact",
            "lessons": "What I learned",
            "evidence_url": "Supporting link",
        }
        help_texts = {
            "technologies": "Separate technologies or skills with commas.",
            "evidence_url": "Optional GitHub, live demo, document or portfolio link.",
        }
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "summary": forms.Textarea(attrs={"rows": 4}),
            "problem": forms.Textarea(attrs={"rows": 4}),
            "personal_contribution": forms.Textarea(attrs={"rows": 5}),
            "technologies": forms.Textarea(attrs={"rows": 2}),
            "outcomes": forms.Textarea(attrs={"rows": 4}),
            "lessons": forms.Textarea(attrs={"rows": 4}),
        }


class ProjectExplanationForm(forms.ModelForm):
    class Meta:
        model = ProjectExplanation
        fields = [
            "quick_pitch",
            "two_minute_answer",
            "architecture",
            "key_decisions",
            "difficult_bug",
            "testing_and_verification",
            "ai_use",
            "tradeoffs",
            "improvements",
            "scaling",
            "likely_follow_ups",
        ]
        labels = {
            "quick_pitch": "30-second explanation",
            "two_minute_answer": "Two-minute explanation",
            "architecture": "Architecture and data flow",
            "key_decisions": "Important technical decisions",
            "difficult_bug": "Difficult bug or failure",
            "testing_and_verification": "Testing and verification",
            "ai_use": "How I used AI",
            "tradeoffs": "Trade-offs",
            "improvements": "What I would improve",
            "scaling": "How I would scale it",
            "likely_follow_ups": "Likely follow-up questions",
        }
        help_texts = {
            "ai_use": (
                "Explain what AI helped with, what you accepted or rejected, "
                "and how you verified the result."
            ),
            "likely_follow_ups": "Add one likely interviewer question per line.",
        }
        widgets = {
            "quick_pitch": forms.Textarea(attrs={"rows": 4}),
            "two_minute_answer": forms.Textarea(attrs={"rows": 8}),
            "architecture": forms.Textarea(attrs={"rows": 5}),
            "key_decisions": forms.Textarea(attrs={"rows": 5}),
            "difficult_bug": forms.Textarea(attrs={"rows": 5}),
            "testing_and_verification": forms.Textarea(attrs={"rows": 5}),
            "ai_use": forms.Textarea(attrs={"rows": 5}),
            "tradeoffs": forms.Textarea(attrs={"rows": 4}),
            "improvements": forms.Textarea(attrs={"rows": 4}),
            "scaling": forms.Textarea(attrs={"rows": 4}),
            "likely_follow_ups": forms.Textarea(attrs={"rows": 5}),
        }


class DecisionRecordForm(forms.ModelForm):
    class Meta:
        model = DecisionRecord
        fields = [
            "title",
            "context",
            "alternatives",
            "decision",
            "rationale",
            "tradeoffs",
            "outcome",
            "would_choose_again",
            "reflection",
        ]
        widgets = {
            "context": forms.Textarea(attrs={"rows": 3}),
            "alternatives": forms.Textarea(attrs={"rows": 3}),
            "decision": forms.Textarea(attrs={"rows": 3}),
            "rationale": forms.Textarea(attrs={"rows": 3}),
            "tradeoffs": forms.Textarea(attrs={"rows": 3}),
            "outcome": forms.Textarea(attrs={"rows": 3}),
            "reflection": forms.Textarea(attrs={"rows": 3}),
        }


class BehaviouralStoryForm(forms.ModelForm):
    class Meta:
        model = BehaviouralStory
        fields = [
            "title",
            "situation",
            "task",
            "actions",
            "result",
            "reflection",
            "competencies",
            "follow_up_questions",
        ]
        labels = {
            "actions": "Actions",
            "competencies": "Competencies demonstrated",
            "follow_up_questions": "Likely follow-up questions",
        }
        help_texts = {
            "competencies": "Separate competencies with commas.",
        }
        widgets = {
            "situation": forms.Textarea(attrs={"rows": 3}),
            "task": forms.Textarea(attrs={"rows": 3}),
            "actions": forms.Textarea(attrs={"rows": 4}),
            "result": forms.Textarea(attrs={"rows": 3}),
            "reflection": forms.Textarea(attrs={"rows": 3}),
            "competencies": forms.Textarea(attrs={"rows": 2}),
            "follow_up_questions": forms.Textarea(attrs={"rows": 3}),
        }


class TopicEvidenceProfileForm(forms.ModelForm):
    class Meta:
        model = TopicEvidenceProfile
        fields = [
            "readiness",
            "personal_angle",
            "interview_angle",
            "evidence_gap",
            "follow_up_questions",
        ]
        labels = {
            "personal_angle": "Where I have used this",
            "interview_angle": "How I would explain it",
            "evidence_gap": "Current evidence gap",
            "follow_up_questions": "Likely follow-up questions",
        }
        widgets = {
            "personal_angle": forms.Textarea(attrs={"rows": 4}),
            "interview_angle": forms.Textarea(attrs={"rows": 4}),
            "evidence_gap": forms.Textarea(attrs={"rows": 3}),
            "follow_up_questions": forms.Textarea(attrs={"rows": 3}),
        }


class UserEvidenceChoiceForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["evidence"].queryset = EvidenceItem.objects.filter(owner=user)


class TopicEvidenceLinkForm(UserEvidenceChoiceForm):
    class Meta:
        model = TopicEvidenceLink
        fields = ["evidence", "connection_note"]
        labels = {"connection_note": "Why this evidence is relevant"}
        widgets = {"connection_note": forms.Textarea(attrs={"rows": 2})}


class QuestionEvidenceLinkForm(UserEvidenceChoiceForm):
    class Meta:
        model = QuestionEvidenceLink
        fields = ["evidence", "answer_angle"]
        labels = {"answer_angle": "How this evidence supports my answer"}
        widgets = {"answer_angle": forms.Textarea(attrs={"rows": 2})}


class GoalEvidenceLinkForm(UserEvidenceChoiceForm):
    class Meta:
        model = GoalEvidenceLink
        fields = ["evidence", "relevance", "framing_notes"]
        labels = {"framing_notes": "How to frame this for the goal"}
        widgets = {"framing_notes": forms.Textarea(attrs={"rows": 2})}
