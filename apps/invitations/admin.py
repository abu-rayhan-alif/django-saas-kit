from django.contrib import admin

from apps.invitations.models import TenantInvitation


@admin.register(TenantInvitation)
class TenantInvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "tenant", "role", "status", "invited_by", "expires_at", "created_at")
    list_filter = ("status", "role", "tenant")
    search_fields = ("email", "tenant__name", "invited_by__email")
    readonly_fields = ("id", "token", "created_at", "accepted_by")
    raw_id_fields = ("invited_by", "accepted_by")
