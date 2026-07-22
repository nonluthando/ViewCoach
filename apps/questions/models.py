import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


def question_import_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    return f"question-imports/{instance.owner_id}/{uuid.uuid4()}{suffix}"


class Question(models.Model):
    class Type(models.TextChoices):
        TECHNICAL = "TECHNICAL", "Technical"
        CONCEPT = "CONCEPT", "Concept"
        BEHAVIOURAL = "BEHAVIOURAL", "Behavioural"
        DEBUG = "DEBUG", "Repository debugging"

    class Difficulty(models.TextChoices):
        EASY = "EASY", "Easy"
        MEDIUM = "MEDIUM", "Medium"
        HARD = "HARD", "Hard"

    class Status(models.TextChoices):
        NEEDS_NOTES = "NEEDS_NOTES", "Needs notes"
        READY_FOR_REVIEW = "READY_FOR_REVIEW", "Ready for review"
        ARCHIVED = "ARCHIVED", "Archived"

    creation_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="questions",
        null=True,
        blank=True,
    )
    import_batch = models.ForeignKey(
        "QuestionImportBatch",
        on_delete=models.SET_NULL,
        related_name="created_questions",
        null=True,
        blank=True,
    )
    is_system = models.BooleanField(default=False)
    system_key = models.SlugField(max_length=140, unique=True, null=True, blank=True)
    title = models.CharField(max_length=180)
    prompt = models.TextField()
    question_type = models.CharField(max_length=20, choices=Type.choices, editable=False)
    company = models.CharField(max_length=120, blank=True)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEEDS_NOTES,
    )
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
            models.Index(
                fields=["is_system", "question_type"],
                name="question_system_type_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        is_system=True,
                        owner__isnull=True,
                        system_key__isnull=False,
                        import_batch__isnull=True,
                    )
                    | Q(
                        is_system=False,
                        owner__isnull=False,
                        system_key__isnull=True,
                    )
                ),
                name="question_system_owner_consistency",
            )
        ]

    def clean(self):
        super().clean()
        if self.__class__ is Question:
            raise ValidationError("Questions must be created using a supported question type.")

        if self.is_system:
            if self.owner_id:
                raise ValidationError("Built-in questions cannot have a user owner.")
            if not self.system_key:
                raise ValidationError("Built-in questions require a system key.")
            if self.import_batch_id:
                raise ValidationError("Built-in questions cannot belong to an import batch.")
        else:
            if not self.owner_id:
                raise ValidationError("User-created questions require an owner.")
            if self.system_key:
                raise ValidationError("User-created questions cannot have a system key.")

    @property
    def specific(self):
        relation_by_type = {
            self.Type.TECHNICAL: "technicalquestion",
            self.Type.CONCEPT: "conceptquestion",
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

    @property
    def source_label(self):
        if self.is_system:
            return "Built-in"
        if self.import_batch_id:
            return "Imported"
        return "My question"

    def readiness_errors(self):
        if self.is_system:
            return []

        errors = []
        if not self.prompt.strip():
            errors.append("problem or question text")

        specific = self.specific
        if specific is self:
            errors.append("type-specific notes")
            return errors

        if self.question_type == self.Type.TECHNICAL:
            has_solution_notes = any(
                value.strip()
                for value in (
                    specific.intuition,
                    specific.brute_force,
                    specific.optimal_approach,
                )
            )
            if not has_solution_notes:
                errors.append("intuition or solution notes")
        elif self.question_type == self.Type.CONCEPT:
            if not specific.canonical_answer.strip():
                errors.append("canonical answer")
        elif self.question_type == self.Type.BEHAVIOURAL:
            if not specific.star_answer.strip():
                errors.append("STAR answer")
        elif self.question_type == self.Type.DEBUG:
            if not specific.fix.strip():
                errors.append("diagnosis or fix")

        return errors

    @property
    def can_mark_ready(self):
        return not self.readiness_errors()

    def mark_ready(self):
        if self.is_system:
            raise ValidationError("Built-in questions use per-user review state.")

        missing_fields = self.readiness_errors()
        if missing_fields:
            raise ValidationError(
                f"Add {', '.join(missing_fields)} before marking this question ready."
            )

        Question.objects.filter(pk=self.pk).update(
            status=self.Status.READY_FOR_REVIEW,
            updated_at=timezone.now(),
        )
        self.status = self.Status.READY_FOR_REVIEW

    def ensure_valid_readiness_status(self):
        if self.is_system:
            return
        if self.status == self.Status.READY_FOR_REVIEW and self.readiness_errors():
            Question.objects.filter(pk=self.pk).update(
                status=self.Status.NEEDS_NOTES,
                updated_at=timezone.now(),
            )
            self.status = self.Status.NEEDS_NOTES

    def __str__(self) -> str:
        return self.title


class TechnicalQuestion(Question):
    topic = models.CharField(max_length=120, blank=True)
    first_hint = models.TextField(blank=True)
    pattern = models.CharField(max_length=120, blank=True)
    data_structure = models.CharField(max_length=120, blank=True)
    intuition = models.TextField(blank=True)
    brute_force = models.TextField(blank=True)
    brute_force_time_complexity = models.CharField(max_length=255, blank=True)
    brute_force_space_complexity = models.CharField(max_length=255, blank=True)
    optimal_approach = models.TextField(blank=True)
    optimal_time_complexity = models.CharField(max_length=255, blank=True)
    optimal_space_complexity = models.CharField(max_length=255, blank=True)
    complexity = models.CharField(max_length=255, blank=True)
    mistakes = models.TextField(blank=True)
    progressive_hints = models.JSONField(default=list, blank=True)
    code = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        self.question_type = Question.Type.TECHNICAL
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "technical question"
        verbose_name_plural = "technical questions"


class ConceptQuestion(Question):
    class Category(models.TextChoices):
        JAVA = "JAVA", "Java"
        PYTHON = "PYTHON", "Python"
        BACKEND = "BACKEND", "Backend / CS fundamentals"
        DATABASES = "DATABASES", "Databases"
        NETWORKING = "NETWORKING", "Networking"
        OPERATING_SYSTEMS = "OPERATING_SYSTEMS", "Operating systems"
        OTHER = "OTHER", "Other"

    category = models.CharField(max_length=30, choices=Category.choices)
    canonical_answer = models.TextField(blank=True)
    key_points = models.JSONField(default=list, blank=True)
    example = models.TextField(blank=True)
    common_misconception = models.TextField(blank=True)
    code_snippet = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        self.question_type = Question.Type.CONCEPT
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "concept question"
        verbose_name_plural = "concept questions"


class BehaviouralQuestion(Question):
    star_answer = models.TextField(blank=True)
    leadership_principles = models.TextField(
        blank=True,
        help_text="Competencies, values or leadership principles this answer demonstrates.",
    )
    stories = models.TextField(blank=True)
    follow_ups = models.TextField(blank=True)
    competencies = models.JSONField(default=list, blank=True)
    star_outline = models.JSONField(default=dict, blank=True)
    personal_detail_prompts = models.JSONField(default=list, blank=True)
    follow_up_questions = models.JSONField(default=list, blank=True)
    common_mistakes = models.JSONField(default=list, blank=True)

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

    repository = models.TextField(blank=True)
    bug_type = models.CharField(max_length=30, choices=BugType.choices, blank=True)
    failing_test_or_symptom = models.TextField(blank=True)
    broken_code = models.TextField(blank=True)
    likely_bug = models.TextField(blank=True)
    reasoning = models.TextField(blank=True)
    fix = models.TextField(blank=True)
    tests = models.TextField(blank=True)
    common_mistake = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        self.question_type = Question.Type.DEBUG
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "debugging question"
        verbose_name_plural = "debugging questions"


class UserQuestionState(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not started"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        READY_FOR_REVIEW = "READY_FOR_REVIEW", "Ready for review"
        ARCHIVED = "ARCHIVED", "Archived"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="question_states",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="user_states",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    bookmarked = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "question"],
                name="unique_user_question_state",
            )
        ]
        indexes = [
            models.Index(
                fields=["user", "status", "-updated_at"],
                name="uqstate_user_status_idx",
            )
        ]

    def mark_in_progress(self):
        if self.status == self.Status.NOT_STARTED:
            self.status = self.Status.IN_PROGRESS
            self.started_at = timezone.now()

    def __str__(self):
        return f"{self.user} · {self.question}"


class UserQuestionNote(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="question_notes",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="user_notes",
    )
    notes = models.TextField(blank=True)
    mistakes = models.TextField(blank=True)
    code_notes = models.TextField(blank=True)
    behavioural_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "question"],
                name="unique_user_question_note",
            )
        ]

    def __str__(self):
        return f"Notes for {self.question} by {self.user}"


class QuestionImportBatch(models.Model):
    class SourceType(models.TextChoices):
        PASTE = "PASTE", "Pasted text"
        TXT = "TXT", "Text file"
        MARKDOWN = "MARKDOWN", "Markdown file"
        CSV = "CSV", "CSV file"
        DOCX = "DOCX", "Word document"
        PDF = "PDF", "PDF document"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        READY_FOR_REVIEW = "READY_FOR_REVIEW", "Ready for review"
        IMPORTING = "IMPORTING", "Importing"
        IMPORTED = "IMPORTED", "Imported"
        FAILED = "FAILED", "Failed"
        ARCHIVED = "ARCHIVED", "Archived"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="question_import_batches",
    )
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    source_filename = models.CharField(max_length=255, blank=True)
    default_question_type = models.CharField(max_length=20, choices=Question.Type.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_question_count = models.PositiveIntegerField(default=0)
    temporary_file = models.FileField(upload_to=question_import_upload_to, blank=True)
    source_text = models.TextField(blank=True)
    failure_message = models.TextField(blank=True)
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    imported_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "status", "-created_at"], name="qimport_owner_status_idx")
        ]

    @property
    def is_editable(self):
        return self.status in {
            self.Status.DRAFT,
            self.Status.READY_FOR_REVIEW,
            self.Status.FAILED,
        }

    @property
    def can_delete(self):
        return self.is_editable

    def __str__(self):
        source = self.source_filename or "Pasted questions"
        return f"{source} · {self.get_status_display()}"


class QuestionImportItem(models.Model):
    batch = models.ForeignKey(
        QuestionImportBatch,
        on_delete=models.CASCADE,
        related_name="items",
    )
    position = models.PositiveIntegerField()
    generated_title = models.CharField(max_length=180)
    question_text = models.TextField()
    normalized_text = models.TextField(blank=True)
    question_type = models.CharField(max_length=20, choices=Question.Type.choices)
    is_included = models.BooleanField(default=True)
    duplicate_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "position"],
                name="unique_question_import_position",
            )
        ]

    def __str__(self):
        return self.generated_title
