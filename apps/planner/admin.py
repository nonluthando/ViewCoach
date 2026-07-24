from django.contrib import admin

from .models import StudyPlan, StudyRecommendation, StudySession


class StudyRecommendationInline(admin.TabularInline):
    model = StudyRecommendation
    extra = 0
    fields = (
        "position",
        "kind",
        "title",
        "estimated_minutes",
        "priority_score",
        "completed_at",
    )
    readonly_fields = ("completed_at",)


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "plan_date",
        "time_budget_minutes",
        "status",
        "generated_at",
    )
    list_filter = ("status", "plan_date")
    search_fields = ("user__email",)
    raw_id_fields = ("user",)
    inlines = (StudyRecommendationInline,)


@admin.register(StudyRecommendation)
class StudyRecommendationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "plan",
        "kind",
        "estimated_minutes",
        "priority_score",
        "completed_at",
    )
    list_filter = ("kind", "completed_at")
    search_fields = ("title", "plan__user__email")
    raw_id_fields = ("plan", "question", "topic")


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = (
        "plan",
        "started_at",
        "ended_at",
        "completed_recommendation_count",
    )
    list_filter = ("started_at", "ended_at")
    raw_id_fields = ("plan",)
