from django.contrib import admin

from apps.rbac.models import UserTenantRole


@admin.register(UserTenantRole)
class UserTenantRoleAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("user", "tenant", "role", "assigned_by", "created_at")
    list_filter = ("role", "tenant")
    search_fields = ("user__username", "tenant__name")
    raw_id_fields = ("user", "tenant", "assigned_by")
