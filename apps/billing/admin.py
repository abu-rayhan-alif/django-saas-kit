from django.contrib import admin

from apps.billing.models import Plan, Subscription, WebhookEvent


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "max_members", "max_storage_mb", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug", "stripe_price_id"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["tenant", "plan", "status", "stripe_customer_id", "current_period_end", "updated_at"]
    list_filter = ["status", "plan"]
    search_fields = ["tenant__name", "stripe_customer_id", "stripe_subscription_id"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ["stripe_event_id", "event_type", "processed_at"]
    list_filter = ["event_type"]
    search_fields = ["stripe_event_id"]
    readonly_fields = ["stripe_event_id", "event_type", "processed_at", "payload"]
