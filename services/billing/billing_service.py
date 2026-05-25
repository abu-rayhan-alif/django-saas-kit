"""Billing use-cases — no HTTP dependencies."""

from __future__ import annotations

from datetime import timedelta

import structlog
from django.db import transaction
from django.utils import timezone

log = structlog.get_logger(__name__)

_GRACE_PERIOD_DAYS = 7


class BillingService:
    """Processes Stripe webhook events and updates Subscription state."""

    @staticmethod
    def process_event(event_type: str, event_data: dict) -> None:
        """Dispatch a Stripe event to the appropriate handler."""
        handlers = {
            "customer.subscription.created": BillingService._on_subscription_created,
            "customer.subscription.updated": BillingService._on_subscription_updated,
            "customer.subscription.deleted": BillingService._on_subscription_canceled,
            "invoice.payment_succeeded": BillingService._on_payment_succeeded,
            "invoice.payment_failed": BillingService._on_payment_failed,
            "customer.subscription.trial_will_end": BillingService._on_trial_ending,
        }
        handler = handlers.get(event_type)
        if handler:
            handler(event_data)
        else:
            log.warning("billing.unhandled_event_type", event_type=event_type)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    @staticmethod
    def _on_subscription_created(data: dict) -> None:
        from apps.billing.models import Subscription

        obj = data.get("object", {})
        stripe_sub_id: str = obj.get("id", "")
        customer_id: str = obj.get("customer", "")
        status: str = obj.get("status", "active")

        with transaction.atomic():
            sub = (
                Subscription.objects.select_for_update()
                .filter(stripe_customer_id=customer_id)
                .first()
            )
            if sub is None:
                log.warning("billing.subscription_created_no_tenant", customer_id=customer_id)
                return

            sub.stripe_subscription_id = stripe_sub_id
            sub.status = status
            sub.stripe_price_id = (
                (obj.get("items", {}).get("data") or [{}])[0].get("price", {}).get("id", "")
            )
            BillingService._apply_period(sub, obj)
            sub.save()
        from apps.audit.models import AuditLog  # noqa: PLC0415

        from services.audit import AuditService  # noqa: PLC0415

        AuditService.log(
            AuditLog.Action.SUBSCRIPTION_CREATED,
            tenant=sub.tenant,
            resource_type="Subscription",
            resource_id=str(sub.pk),
            metadata={"status": status, "stripe_sub_id": stripe_sub_id},
        )
        log.info("billing.subscription_created", tenant_id=str(sub.tenant_id), status=status)

    @staticmethod
    def _on_subscription_updated(data: dict) -> None:
        from apps.billing.models import Subscription

        obj = data.get("object", {})
        stripe_sub_id: str = obj.get("id", "")
        status: str = obj.get("status", "active")

        with transaction.atomic():
            try:
                sub = Subscription.objects.select_for_update().get(
                    stripe_subscription_id=stripe_sub_id
                )
            except Subscription.DoesNotExist:
                log.warning("billing.subscription_not_found", stripe_sub_id=stripe_sub_id)
                return

            sub.status = status
            sub.cancel_at_period_end = obj.get("cancel_at_period_end", False)
            BillingService._apply_period(sub, obj)
            sub.save()
        log.info("billing.subscription_updated", tenant_id=str(sub.tenant_id), status=status)

    @staticmethod
    def _on_subscription_canceled(data: dict) -> None:
        from apps.billing.models import Subscription

        obj = data.get("object", {})
        stripe_sub_id: str = obj.get("id", "")

        with transaction.atomic():
            try:
                sub = Subscription.objects.select_for_update().get(
                    stripe_subscription_id=stripe_sub_id
                )
            except Subscription.DoesNotExist:
                return

            sub.status = Subscription.Status.CANCELED
            sub.grace_period_end = None
            sub.save(update_fields=["status", "grace_period_end", "updated_at"])
        from apps.audit.models import AuditLog  # noqa: PLC0415

        from services.audit import AuditService  # noqa: PLC0415

        AuditService.log(
            AuditLog.Action.SUBSCRIPTION_CANCELED,
            tenant=sub.tenant,
            resource_type="Subscription",
            resource_id=str(sub.pk),
        )
        log.info("billing.subscription_canceled", tenant_id=str(sub.tenant_id))

    @staticmethod
    def _on_payment_succeeded(data: dict) -> None:
        from apps.billing.models import Subscription

        obj = data.get("object", {})
        stripe_sub_id: str = obj.get("subscription", "")
        if not stripe_sub_id:
            return

        with transaction.atomic():
            try:
                sub = Subscription.objects.select_for_update().get(
                    stripe_subscription_id=stripe_sub_id
                )
            except Subscription.DoesNotExist:
                return

            sub.status = Subscription.Status.ACTIVE
            sub.grace_period_end = None
            sub.save(update_fields=["status", "grace_period_end", "updated_at"])
        log.info("billing.payment_succeeded", tenant_id=str(sub.tenant_id))

    @staticmethod
    def _on_payment_failed(data: dict) -> None:
        from apps.billing.models import Subscription
        from apps.billing.tasks import send_dunning_email

        obj = data.get("object", {})
        stripe_sub_id: str = obj.get("subscription", "")
        if not stripe_sub_id:
            return

        with transaction.atomic():
            try:
                sub = Subscription.objects.select_for_update().get(
                    stripe_subscription_id=stripe_sub_id
                )
            except Subscription.DoesNotExist:
                return

            sub.status = Subscription.Status.PAST_DUE
            sub.grace_period_end = timezone.now() + timedelta(days=_GRACE_PERIOD_DAYS)
            sub.save(update_fields=["status", "grace_period_end", "updated_at"])
            tenant_id = str(sub.tenant_id)
            grace_until = sub.grace_period_end.isoformat()

        send_dunning_email.delay(tenant_id)
        log.info("billing.payment_failed", tenant_id=tenant_id, grace_until=grace_until)

    @staticmethod
    def _on_trial_ending(data: dict) -> None:
        obj = data.get("object", {})
        log.info("billing.trial_ending", stripe_sub_id=obj.get("id"))
        # TODO: send trial-ending notification email

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_period(sub, obj: dict) -> None:
        import datetime

        start_ts = obj.get("current_period_start")
        end_ts = obj.get("current_period_end")
        trial_end_ts = obj.get("trial_end")

        if start_ts:
            sub.current_period_start = datetime.datetime.fromtimestamp(start_ts, tz=datetime.UTC)
        if end_ts:
            sub.current_period_end = datetime.datetime.fromtimestamp(end_ts, tz=datetime.UTC)
        if trial_end_ts:
            sub.trial_end = datetime.datetime.fromtimestamp(trial_end_ts, tz=datetime.UTC)
