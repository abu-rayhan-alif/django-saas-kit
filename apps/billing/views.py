"""Stripe webhook endpoint."""

from __future__ import annotations

import structlog
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.models import WebhookEvent
from apps.billing.tasks import handle_stripe_event

log = structlog.get_logger(__name__)

# Events we handle — all others are acknowledged and ignored
HANDLED_EVENTS: frozenset[str] = frozenset(
    {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.payment_succeeded",
        "invoice.payment_failed",
        "customer.subscription.trial_will_end",
    }
)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    """
    POST /api/v1/billing/webhook/

    Validates the Stripe-Signature header, deduplicates events, and dispatches
    processing to a Celery task so the webhook response is always fast.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request: Request) -> Response:
        import stripe  # imported lazily — only needed if billing is active

        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")

        if not webhook_secret:
            log.error("billing.webhook_secret_missing")
            return Response({"error": "misconfigured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except ValueError:
            log.warning("billing.webhook_invalid_payload")
            return Response({"error": "invalid_payload"}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            log.warning("billing.webhook_invalid_signature")
            return Response({"error": "invalid_signature"}, status=status.HTTP_400_BAD_REQUEST)

        event_id: str = event["id"]
        event_type: str = event["type"]

        if event_type not in HANDLED_EVENTS:
            return Response({"status": "ignored", "type": event_type})

        # Idempotency guard — duplicate delivery is normal for Stripe.
        # get_or_create is atomic: concurrent deliveries can't both insert.
        _, created = WebhookEvent.objects.get_or_create(
            stripe_event_id=event_id,
            defaults={"event_type": event_type, "payload": event["data"]},
        )
        if not created:
            log.info("billing.webhook_duplicate", event_id=event_id)
            return Response({"status": "duplicate"})

        handle_stripe_event.delay(event_id, event_type, dict(event["data"]))
        log.info("billing.webhook_queued", event_id=event_id, event_type=event_type)
        return Response({"status": "queued"})
