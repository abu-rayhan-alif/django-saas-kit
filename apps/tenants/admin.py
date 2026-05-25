from django.contrib import admin

from apps.tenants.models import Domain, Tenant


class DomainInline(admin.TabularInline):  # type: ignore[type-arg]
    model = Domain
    extra = 1
    fields = ("domain", "is_primary")


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "schema_name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "schema_name", "slug")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [DomainInline]


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("domain", "tenant", "is_primary")
    list_filter = ("is_primary",)
    search_fields = ("domain", "tenant__name")
    raw_id_fields = ("tenant",)
