from django.contrib import admin

from .models import ReviewAttempt, ReviewState


@admin.register(ReviewState)
class ReviewStateAdmin(admin.ModelAdmin):
    list_display = (
        "question",
        "user",
        "due_at",
        "interval_days",
        "repetitions",
        "lapses",
    )
    list_filter = ("due_at",)
    search_fields = ("question__title", "user__email")
    raw_id_fields = ("user", "question")


@admin.register(ReviewAttempt)
class ReviewAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "state",
        "rating",
        "reviewed_at",
        "scheduled_due_at",
    )
    list_filter = ("rating", "reviewed_at")
    search_fields = (
        "state__question__title",
        "state__user__email",
    )
    raw_id_fields = ("state",)
