from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "actor_email", "action", "resource_type", "resource_id", "tenant")
    list_filter = ("action", "tenant")
    search_fields = ("actor_email", "resource_id", "metadata")
    readonly_fields = (
        "id",
        "timestamp",
        "actor",
        "actor_email",
        "action",
        "resource_type",
        "resource_id",
        "metadata",
        "ip_address",
        "user_agent",
        "tenant",
    )
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
