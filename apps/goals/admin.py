from django.contrib import admin

from .models import InterviewGoal, InterviewStage


class InterviewStageInline(admin.TabularInline):
    model = InterviewStage
    extra = 0


@admin.register(InterviewGoal)
class InterviewGoalAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "role_title",
        "company",
        "status",
        "is_primary",
    )
    list_filter = ("goal_type", "status", "is_primary")
    search_fields = ("title", "role_title", "company", "user__email")
    filter_horizontal = ("roadmaps",)
    inlines = [InterviewStageInline]


@admin.register(InterviewStage)
class InterviewStageAdmin(admin.ModelAdmin):
    list_display = (
        "goal",
        "stage_type",
        "scheduled_for",
        "is_current",
        "completed_at",
    )
    list_filter = ("stage_type", "is_current", "completed_at")
