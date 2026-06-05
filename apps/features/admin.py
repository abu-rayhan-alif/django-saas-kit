from django.contrib import admin

from apps.features.models import TenantFeatureFlag


@admin.register(TenantFeatureFlag)
class TenantFeatureFlagAdmin(admin.ModelAdmin):
    list_display = ("flag_name", "tenant", "is_enabled", "source", "updated_at")
    list_filter = ("is_enabled", "source", "flag_name")
    search_fields = ("flag_name", "tenant__name", "note")
    ordering = ("flag_name", "tenant__name")
    readonly_fields = ("created_at", "updated_at")
