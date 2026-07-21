import uuid

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models


class Question(models.Model):
    class Type(models.TextChoices):
        TECHNICAL = "TECHNICAL", "Technical"
        BEHAVIOURAL = "BEHAVIOURAL", "Behavioural"
        DEBUG = "DEBUG", "Repository debugging"

    class Difficulty(models.TextChoices):
        EASY = "EASY", "Easy"
        MEDIUM = "MEDIUM", "Medium"
        HARD = "HARD", "Hard"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        ARCHIVED = "ARCHIVED", "Archived"

    creation_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    title = models.CharField(max_length=180)
    prompt = models.TextField()
    question_type = models.CharField(max_length=20, choices=Type.choices, editable=False)
    company = models.CharField(max_length=120, blank=True)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]
        indexes = [
            models.Index(
                fields=["owner", "status", "-updated_at"],
                name="question_owner_status_idx",
            ),
            models.Index(fields=["owner", "question_type"], name="question_owner_type_idx"),
        ]

    def clean(self):
        super().clean()
        if self.__class__ is Question:
            raise ValidationError("Questions must be created using a supported question type.")

    @property
    def specific(self):
        relation_by_type = {
            self.Type.TECHNICAL: "technicalquestion",
            self.Type.BEHAVIOURAL: "behaviouralquestion",
            self.Type.DEBUG: "debugquestion",
        }
        relation_name = relation_by_type.get(self.question_type)
        if not relation_name:
            return self

        try:
            return getattr(self, relation_name)
        except ObjectDoesNotExist:
            return self

    def __str__(self) -> str:
        return self.title


class TechnicalQuestion(Question):

    topic = models.CharField(max_length=120, blank=True)
    first_hint = models.TextField(blank=True)
    pattern = models.CharField(max_length=120, blank=True)
    data_structure = models.CharField(max_length=120, blank=True)
    intuition = models.TextField(blank=True)
    brute_force = models.TextField(blank=True)
    optimal_approach = models.TextField(blank=True)
    complexity = models.CharField(max_length=255, blank=True)
    mistakes = models.TextField(blank=True)
    code = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        self.question_type = Question.Type.TECHNICAL
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "technical question"
        verbose_name_plural = "technical questions"


class BehaviouralQuestion(Question):

    star_answer = models.TextField(blank=True)
    leadership_principles = models.TextField(
        blank=True,
        help_text="Competencies, values or leadership principles this answer demonstrates.",
    )
    stories = models.TextField(blank=True)
    follow_ups = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        self.question_type = Question.Type.BEHAVIOURAL
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "behavioural question"
        verbose_name_plural = "behavioural questions"


class DebugQuestion(Question):
    class BugType(models.TextChoices):
        SORTING = "SORTING", "Broken sorting"
        MISSING_FIELD = "MISSING_FIELD", "Missing field"
        WRONG_COMPARISON = "WRONG_COMPARISON", "Wrong comparison"
        INCORRECT_DEFAULT = "INCORRECT_DEFAULT", "Incorrect default"
        NULL_HANDLING = "NULL_HANDLING", "Null handling"
        KEY_TYPO = "KEY_TYPO", "Dictionary key typo"
        OFF_BY_ONE = "OFF_BY_ONE", "Off-by-one"
        API_RESPONSE = "API_RESPONSE", "Wrong API response"
        OTHER = "OTHER", "Other"

    repository = models.CharField(max_length=160, blank=True)
    bug_type = models.CharField(max_length=30, choices=BugType.choices, blank=True)
    broken_code = models.TextField(blank=True)
    fix = models.TextField(blank=True)
    tests = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        self.question_type = Question.Type.DEBUG
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "debugging question"
        verbose_name_plural = "debugging questions"
