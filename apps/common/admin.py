from django.contrib import admin

from apps.common.models import Record


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ("title", "is_deleted", "created_at", "updated_at")
    list_filter = ("is_deleted",)
    search_fields = ("title",)
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
