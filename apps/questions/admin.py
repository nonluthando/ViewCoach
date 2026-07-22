from django.contrib import admin

from .models import (
    BehaviouralQuestion,
    DebugQuestion,
    Question,
    QuestionImportBatch,
    QuestionImportItem,
    TechnicalQuestion,
)


class TypedQuestionAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "status", "company", "updated_at")
    list_filter = ("status", "difficulty", "company")
    search_fields = ("title", "prompt", "owner__email", "company")
    readonly_fields = ("question_type", "import_batch", "created_at", "updated_at")
    autocomplete_fields = ("owner",)

    def save_model(self, request, obj, form, change):
        if not change and not obj.owner_id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)


@admin.register(TechnicalQuestion)
class TechnicalQuestionAdmin(TypedQuestionAdmin):
    list_display = TypedQuestionAdmin.list_display + ("topic", "pattern")
    search_fields = TypedQuestionAdmin.search_fields + ("topic", "pattern")


@admin.register(BehaviouralQuestion)
class BehaviouralQuestionAdmin(TypedQuestionAdmin):
    search_fields = TypedQuestionAdmin.search_fields + (
        "leadership_principles",
        "stories",
    )


@admin.register(DebugQuestion)
class DebugQuestionAdmin(TypedQuestionAdmin):
    list_display = TypedQuestionAdmin.list_display + ("repository", "bug_type")
    list_filter = TypedQuestionAdmin.list_filter + ("bug_type",)
    search_fields = TypedQuestionAdmin.search_fields + ("repository", "bug_type")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "question_type", "status", "updated_at")
    list_filter = ("question_type", "status", "difficulty")
    search_fields = ("title", "prompt", "owner__email", "company")
    readonly_fields = (
        "owner",
        "import_batch",
        "title",
        "prompt",
        "question_type",
        "company",
        "difficulty",
        "status",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class QuestionImportItemInline(admin.TabularInline):
    model = QuestionImportItem
    extra = 0
    readonly_fields = (
        "position",
        "generated_title",
        "question_text",
        "question_type",
        "is_included",
        "duplicate_reason",
    )
    can_delete = False


@admin.register(QuestionImportBatch)
class QuestionImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "source_type",
        "status",
        "created_question_count",
        "created_at",
    )
    list_filter = ("source_type", "status", "default_question_type")
    search_fields = ("owner__email", "source_filename")
    readonly_fields = (
        "idempotency_key",
        "created_question_count",
        "created_at",
        "updated_at",
        "imported_at",
        "archived_at",
    )
    inlines = (QuestionImportItemInline,)
