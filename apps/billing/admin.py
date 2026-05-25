from django.contrib import admin

from apps.billing.models import Subscription, WebhookEvent


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["tenant", "status", "stripe_customer_id", "current_period_end", "updated_at"]
    list_filter = ["status"]
    search_fields = ["tenant__name", "stripe_customer_id", "stripe_subscription_id"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ["stripe_event_id", "event_type", "processed_at"]
    list_filter = ["event_type"]
    search_fields = ["stripe_event_id"]
    readonly_fields = ["stripe_event_id", "event_type", "processed_at", "payload"]
