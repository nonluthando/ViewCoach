from django.contrib import admin

from .models import (
    AIPrepAnswer,
    BehaviouralStory,
    DecisionRecord,
    EvidenceItem,
    GoalEvidenceLink,
    ProjectExplanation,
    QuestionEvidenceLink,
    TopicEvidenceLink,
    TopicEvidenceProfile,
)


class DecisionRecordInline(admin.StackedInline):
    model = DecisionRecord
    extra = 0


class BehaviouralStoryInline(admin.StackedInline):
    model = BehaviouralStory
    extra = 0


class ProjectExplanationInline(admin.StackedInline):
    model = ProjectExplanation
    extra = 0
    max_num = 1


@admin.register(EvidenceItem)
class EvidenceItemAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "source_type", "organisation", "updated_at")
    list_filter = ("source_type",)
    search_fields = ("title", "owner__email", "organisation", "technologies")
    inlines = [ProjectExplanationInline, DecisionRecordInline, BehaviouralStoryInline]


@admin.register(AIPrepAnswer)
class AIPrepAnswerAdmin(admin.ModelAdmin):
    list_display = ("user", "question_key", "supporting_evidence", "updated_at")
    search_fields = ("user__email", "question_key", "answer_notes")
    raw_id_fields = ("user", "supporting_evidence")


@admin.register(TopicEvidenceProfile)
class TopicEvidenceProfileAdmin(admin.ModelAdmin):
    list_display = ("topic", "user", "readiness", "updated_at")
    list_filter = ("readiness",)
    search_fields = ("topic__title", "user__email")


@admin.register(TopicEvidenceLink)
class TopicEvidenceLinkAdmin(admin.ModelAdmin):
    list_display = ("profile", "evidence", "created_at")


@admin.register(QuestionEvidenceLink)
class QuestionEvidenceLinkAdmin(admin.ModelAdmin):
    list_display = ("question", "evidence", "user", "created_at")
    search_fields = ("question__title", "evidence__title", "user__email")


@admin.register(GoalEvidenceLink)
class GoalEvidenceLinkAdmin(admin.ModelAdmin):
    list_display = ("goal", "evidence", "user", "relevance", "created_at")
    list_filter = ("relevance",)
