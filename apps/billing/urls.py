from django.urls import path

from apps.billing.views import StripeWebhookView

urlpatterns = [
    path("webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
]
