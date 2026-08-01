from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.goals.models import InterviewGoal
from apps.questions.models import Question
from apps.roadmaps.models import RoadmapTopic

from .ai_prep import AI_INTERVIEW_QUESTION_BY_KEY


class EvidenceItem(models.Model):
    class SourceType(models.TextChoices):
        PROJECT = "PROJECT", "Project"
        WORK = "WORK", "Work experience"
        COURSEWORK = "COURSEWORK", "Coursework"
        LEADERSHIP = "LEADERSHIP", "Leadership or teamwork"
        INCIDENT = "INCIDENT", "Technical incident"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="evidence_items",
    )
    source_type = models.CharField(max_length=16, choices=SourceType.choices)
    title = models.CharField(max_length=180)
    organisation = models.CharField(max_length=140, blank=True)
    role_or_context = models.CharField(max_length=180, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    summary = models.TextField(blank=True)
    problem = models.TextField(blank=True)
    personal_contribution = models.TextField(blank=True)
    technologies = models.TextField(blank=True)
    outcomes = models.TextField(blank=True)
    lessons = models.TextField(blank=True)
    evidence_url = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at", "pk"]
        indexes = [
            models.Index(
                fields=["owner", "source_type", "-updated_at"],
                name="evidence_owner_type_idx",
            )
        ]

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date cannot be before the start date."})

    @property
    def technology_list(self):
        return [item.strip() for item in self.technologies.split(",") if item.strip()]

    def get_absolute_url(self):
        return reverse("evidence:detail", args=[self.pk])

    def __str__(self):
        return self.title


class ProjectExplanation(models.Model):
    evidence = models.OneToOneField(
        EvidenceItem,
        on_delete=models.CASCADE,
        related_name="project_explanation",
    )
    quick_pitch = models.TextField(
        blank=True,
        help_text="A concise explanation suitable for a 30-second answer.",
    )
    two_minute_answer = models.TextField(
        blank=True,
        help_text="The complete interview-ready project explanation.",
    )
    architecture = models.TextField(blank=True)
    key_decisions = models.TextField(blank=True)
    difficult_bug = models.TextField(blank=True)
    testing_and_verification = models.TextField(blank=True)
    ai_use = models.TextField(blank=True)
    tradeoffs = models.TextField(blank=True)
    improvements = models.TextField(blank=True)
    scaling = models.TextField(blank=True)
    likely_follow_ups = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.evidence_id and self.evidence.source_type != EvidenceItem.SourceType.PROJECT:
            raise ValidationError(
                {"evidence": "Project explanations can only be attached to project evidence."}
            )

    @property
    def has_deep_dive(self):
        return any(
            value.strip()
            for value in (
                self.architecture,
                self.key_decisions,
                self.difficult_bug,
                self.testing_and_verification,
                self.ai_use,
                self.tradeoffs,
                self.improvements,
                self.scaling,
                self.likely_follow_ups,
            )
        )

    def __str__(self):
        return f"Interview explanation: {self.evidence}"


class AIPrepAnswer(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_prep_answers",
    )
    question_key = models.SlugField(max_length=100)
    answer_notes = models.TextField(blank=True)
    supporting_evidence = models.ForeignKey(
        EvidenceItem,
        on_delete=models.SET_NULL,
        related_name="ai_prep_answers",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["question_key"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "question_key"],
                name="unique_user_ai_prep_answer",
            )
        ]
        indexes = [
            models.Index(
                fields=["user", "question_key"],
                name="ai_prep_user_question_idx",
            )
        ]

    def clean(self):
        super().clean()
        if self.question_key not in AI_INTERVIEW_QUESTION_BY_KEY:
            raise ValidationError({"question_key": "Unknown AI interview question."})
        if (
            self.user_id
            and self.supporting_evidence_id
            and self.supporting_evidence.owner_id != self.user_id
        ):
            raise ValidationError(
                {"supporting_evidence": "Supporting evidence must belong to the user."}
            )

    @property
    def question(self):
        return AI_INTERVIEW_QUESTION_BY_KEY.get(self.question_key)

    @property
    def is_prepared(self):
        return bool(self.answer_notes.strip())

    def __str__(self):
        question = self.question
        label = question.question if question else self.question_key
        return f"{self.user}: {label}"


class AIRepositoryPracticeAttempt(models.Model):
    class ScenarioType(models.TextChoices):
        DEBUGGING = "DEBUGGING", "Debugging failures"
        FEATURE = "FEATURE", "Small feature"
        MIXED = "MIXED", "Debugging and feature"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_repository_practice_attempts",
    )
    title = models.CharField(max_length=180)
    scenario_type = models.CharField(
        max_length=12,
        choices=ScenarioType.choices,
        default=ScenarioType.MIXED,
    )
    practiced_on = models.DateField(default=timezone.localdate)
    duration_minutes = models.PositiveSmallIntegerField(default=60)
    tests_fixed = models.PositiveSmallIntegerField(default=0)
    feature_completed = models.BooleanField(default=False)
    full_suite_passed = models.BooleanField(default=False)
    ai_use_note = models.TextField(blank=True)
    reflection = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-practiced_on", "-created_at"]
        indexes = [
            models.Index(
                fields=["user", "-practiced_on"],
                name="ai_repo_user_practice_idx",
            )
        ]

    def clean(self):
        super().clean()
        if not 15 <= self.duration_minutes <= 180:
            raise ValidationError(
                {"duration_minutes": "Practice duration must be between 15 and 180 minutes."}
            )

    @property
    def outcome_label(self):
        if self.full_suite_passed and self.feature_completed:
            return "Completed and verified"
        if self.full_suite_passed:
            return "Fixes verified"
        if self.tests_fixed or self.feature_completed:
            return "Partially completed"
        return "Attempt recorded"

    def __str__(self):
        return f"{self.user}: {self.title}"


class DecisionRecord(models.Model):
    class RepeatChoice(models.TextChoices):
        YES = "YES", "Yes"
        NO = "NO", "No"
        UNSURE = "UNSURE", "Unsure"

    evidence = models.ForeignKey(
        EvidenceItem,
        on_delete=models.CASCADE,
        related_name="decisions",
    )
    title = models.CharField(max_length=180)
    context = models.TextField(blank=True)
    alternatives = models.TextField(blank=True)
    decision = models.TextField()
    rationale = models.TextField(blank=True)
    tradeoffs = models.TextField(blank=True)
    outcome = models.TextField(blank=True)
    would_choose_again = models.CharField(
        max_length=8,
        choices=RepeatChoice.choices,
        default=RepeatChoice.UNSURE,
    )
    reflection = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "pk"]

    def __str__(self):
        return self.title


class BehaviouralStory(models.Model):
    INTERVIEW_READY_FIELDS = (
        ("situation", "Situation"),
        ("actions", "Actions"),
        ("result", "Result"),
        ("reflection", "Reflection"),
        ("competencies", "Competencies"),
        ("follow_up_questions", "Follow-up questions"),
    )

    evidence = models.ForeignKey(
        EvidenceItem,
        on_delete=models.CASCADE,
        related_name="behavioural_stories",
    )
    title = models.CharField(max_length=180)
    situation = models.TextField()
    task = models.TextField(blank=True)
    actions = models.TextField()
    result = models.TextField(blank=True)
    reflection = models.TextField(blank=True)
    competencies = models.TextField(blank=True)
    follow_up_questions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "pk"]

    @property
    def competency_list(self):
        return [item.strip() for item in self.competencies.split(",") if item.strip()]

    @property
    def follow_up_question_list(self):
        return [item.strip() for item in self.follow_up_questions.splitlines() if item.strip()]

    @property
    def completed_interview_sections(self):
        return sum(
            bool(getattr(self, field_name).strip()) for field_name, _ in self.INTERVIEW_READY_FIELDS
        )

    @property
    def total_interview_sections(self):
        return len(self.INTERVIEW_READY_FIELDS)

    @property
    def is_interview_ready(self):
        return self.completed_interview_sections == self.total_interview_sections

    @property
    def missing_interview_sections(self):
        return [
            label
            for field_name, label in self.INTERVIEW_READY_FIELDS
            if not getattr(self, field_name).strip()
        ]

    def __str__(self):
        return self.title


class TopicEvidenceProfile(models.Model):
    class Readiness(models.TextChoices):
        KNOWLEDGE_ONLY = "KNOWLEDGE_ONLY", "Knowledge only"
        PROJECT_EVIDENCE = "PROJECT_EVIDENCE", "Project evidence"
        WORK_EVIDENCE = "WORK_EVIDENCE", "Work evidence"
        INTERVIEW_READY = "INTERVIEW_READY", "Interview ready"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="topic_evidence_profiles",
    )
    topic = models.ForeignKey(
        RoadmapTopic,
        on_delete=models.CASCADE,
        related_name="evidence_profiles",
    )
    readiness = models.CharField(
        max_length=20,
        choices=Readiness.choices,
        default=Readiness.KNOWLEDGE_ONLY,
    )
    personal_angle = models.TextField(blank=True)
    interview_angle = models.TextField(blank=True)
    evidence_gap = models.TextField(blank=True)
    follow_up_questions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "topic"],
                name="unique_user_topic_evidence",
            )
        ]
        indexes = [
            models.Index(
                fields=["user", "readiness", "-updated_at"],
                name="topic_evid_user_ready_idx",
            )
        ]

    def __str__(self):
        return f"{self.user}: {self.topic}"


class TopicEvidenceLink(models.Model):
    profile = models.ForeignKey(
        TopicEvidenceProfile,
        on_delete=models.CASCADE,
        related_name="evidence_links",
    )
    evidence = models.ForeignKey(
        EvidenceItem,
        on_delete=models.CASCADE,
        related_name="topic_links",
    )
    connection_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "evidence"],
                name="unique_topic_evidence_link",
            )
        ]

    def clean(self):
        super().clean()
        if self.profile_id and self.evidence_id:
            if self.profile.user_id != self.evidence.owner_id:
                raise ValidationError("Evidence and topic profile must belong to the same user.")

    def __str__(self):
        return f"{self.profile.topic}: {self.evidence}"


class QuestionEvidenceLink(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="question_evidence_links",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="evidence_links",
    )
    evidence = models.ForeignKey(
        EvidenceItem,
        on_delete=models.CASCADE,
        related_name="question_links",
    )
    answer_angle = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "question", "evidence"],
                name="unique_question_evidence_link",
            )
        ]
        indexes = [
            models.Index(
                fields=["user", "question"],
                name="quest_evid_user_question_idx",
            )
        ]

    def clean(self):
        super().clean()
        if self.user_id and self.evidence_id and self.user_id != self.evidence.owner_id:
            raise ValidationError("Evidence must belong to the linked user.")
        if self.user_id and self.question_id:
            has_access = self.question.is_system or self.question.owner_id == self.user_id
            if not has_access:
                raise ValidationError("The user cannot access this question.")

    def __str__(self):
        return f"{self.question}: {self.evidence}"


class GoalEvidenceLink(models.Model):
    class Relevance(models.TextChoices):
        CORE = "CORE", "Core evidence"
        SUPPORTING = "SUPPORTING", "Supporting evidence"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="goal_evidence_links",
    )
    goal = models.ForeignKey(
        InterviewGoal,
        on_delete=models.CASCADE,
        related_name="evidence_links",
    )
    evidence = models.ForeignKey(
        EvidenceItem,
        on_delete=models.CASCADE,
        related_name="goal_links",
    )
    relevance = models.CharField(
        max_length=12,
        choices=Relevance.choices,
        default=Relevance.SUPPORTING,
    )
    framing_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["relevance", "created_at", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "goal", "evidence"],
                name="unique_goal_evidence_link",
            )
        ]
        indexes = [
            models.Index(
                fields=["user", "goal", "relevance"],
                name="goal_evid_user_goal_idx",
            )
        ]

    def clean(self):
        super().clean()
        if self.user_id and self.goal_id and self.user_id != self.goal.user_id:
            raise ValidationError("Goal must belong to the linked user.")
        if self.user_id and self.evidence_id and self.user_id != self.evidence.owner_id:
            raise ValidationError("Evidence must belong to the linked user.")

    def __str__(self):
        return f"{self.goal}: {self.evidence}"
