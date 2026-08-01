from django.contrib import admin

from .models import MockInterview, MockInterviewItem


class MockInterviewItemInline(admin.TabularInline):
    model = MockInterviewItem
    extra = 0
    fields = (
        "position",
        "question_title",
        "question_type",
        "assessment",
        "answered_at",
    )
    readonly_fields = fields
    can_delete = False
    show_change_link = True


@admin.register(MockInterview)
class MockInterviewAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "goal",
        "focus",
        "status",
        "question_count",
        "duration_minutes",
        "created_at",
    )
    list_filter = (
        "focus",
        "status",
        "created_at",
    )
    search_fields = ("user__email",)
    readonly_fields = (
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
    )
    inlines = [MockInterviewItemInline]


@admin.register(MockInterviewItem)
class MockInterviewItemAdmin(admin.ModelAdmin):
    list_display = (
        "question_title",
        "interview",
        "position",
        "question_type",
        "assessment",
        "answered_at",
    )
    list_filter = (
        "question_type",
        "assessment",
    )
    search_fields = (
        "question_title",
        "prompt_snapshot",
        "interview__user__email",
    )
    readonly_fields = (
        "created_at",
        "answered_at",
    )
