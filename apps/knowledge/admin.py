from django.contrib import admin

from .models import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeIngestionRun,
    KnowledgeQueryLog,
)


class KnowledgeChunkInline(admin.TabularInline):
    model = KnowledgeChunk
    fields = (
        "position",
        "heading",
        "character_count",
        "token_estimate",
    )
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "status",
        "chunk_count",
        "embedding_model",
        "last_ingested_at",
    )
    list_filter = ("status", "category", "embedding_model")
    search_fields = (
        "title",
        "summary",
        "body_markdown",
        "source_path",
    )
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = (
        "content_checksum",
        "embedding_model",
        "chunk_count",
        "last_ingested_at",
        "created_at",
        "updated_at",
    )
    inlines = [KnowledgeChunkInline]


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = (
        "document",
        "position",
        "heading",
        "character_count",
        "token_estimate",
    )
    list_filter = ("document__category", "document__status")
    search_fields = (
        "document__title",
        "heading",
        "content",
    )
    readonly_fields = (
        "document",
        "position",
        "heading",
        "content",
        "content_checksum",
        "character_count",
        "token_estimate",
        "created_at",
        "updated_at",
    )
    exclude = ("embedding",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(KnowledgeIngestionRun)
class KnowledgeIngestionRunAdmin(admin.ModelAdmin):
    list_display = (
        "source_label",
        "status",
        "documents_seen",
        "documents_ingested",
        "documents_skipped",
        "chunks_created",
        "started_at",
        "finished_at",
    )
    list_filter = ("status",)
    search_fields = ("source_label", "error_message")
    readonly_fields = (
        "source_label",
        "status",
        "documents_seen",
        "documents_ingested",
        "documents_skipped",
        "chunks_created",
        "error_message",
        "started_at",
        "finished_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False



@admin.register(KnowledgeQueryLog)
class KnowledgeQueryLogAdmin(admin.ModelAdmin):
    list_display = (
        "short_question",
        "user",
        "status",
        "generation_model",
        "top_similarity",
        "latency_ms",
        "created_at",
    )
    list_filter = (
        "status",
        "generation_model",
        "created_at",
    )
    search_fields = (
        "question",
        "answer",
        "user__email",
        "error_message",
    )
    readonly_fields = (
        "user",
        "question",
        "answer",
        "status",
        "generation_model",
        "retrieved_chunk_ids",
        "citations",
        "top_similarity",
        "latency_ms",
        "error_message",
        "created_at",
    )
    list_select_related = ("user",)

    @admin.display(description="Question")
    def short_question(self, obj):
        return obj.question[:80]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
