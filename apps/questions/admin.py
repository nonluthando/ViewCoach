from django.contrib import admin

from .models import BehaviouralQuestion, DebugQuestion, Question, TechnicalQuestion


class TypedQuestionAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "status", "company", "updated_at")
    list_filter = ("status", "difficulty", "company")
    search_fields = ("title", "prompt", "owner__email", "company")
    readonly_fields = ("question_type", "created_at", "updated_at")
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
