from django.contrib import admin

from .models import Roadmap, RoadmapSection, RoadmapTopic, UserRoadmap, UserTopicProgress


class RoadmapTopicInline(admin.TabularInline):
    model = RoadmapTopic
    extra = 0
    fields = ("position", "title", "slug")
    ordering = ("position",)


@admin.register(RoadmapSection)
class RoadmapSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "roadmap", "position")
    list_filter = ("roadmap__kind", "roadmap")
    search_fields = ("title", "roadmap__title")
    ordering = ("roadmap", "position")
    inlines = (RoadmapTopicInline,)


@admin.register(Roadmap)
class RoadmapAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "is_system", "is_published", "position")
    list_filter = ("kind", "is_system", "is_published")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("kind", "position", "title")


@admin.register(RoadmapTopic)
class RoadmapTopicAdmin(admin.ModelAdmin):
    list_display = ("title", "section", "position")
    list_filter = ("section__roadmap",)
    search_fields = ("title", "section__title", "section__roadmap__title")
    ordering = ("section", "position")


@admin.register(UserRoadmap)
class UserRoadmapAdmin(admin.ModelAdmin):
    list_display = ("user", "roadmap", "status", "started_at", "completed_at")
    list_filter = ("status", "roadmap__kind")
    search_fields = ("user__email", "roadmap__title")
    raw_id_fields = ("user", "roadmap")


@admin.register(UserTopicProgress)
class UserTopicProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "topic", "status", "updated_at")
    list_filter = ("status", "topic__section__roadmap")
    search_fields = ("user__email", "topic__title")
    raw_id_fields = ("user", "topic")
