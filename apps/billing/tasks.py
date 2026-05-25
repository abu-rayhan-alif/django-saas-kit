"""Celery tasks for async Stripe webhook processing and dunning."""

from __future__ import annotations

from typing import Any

import structlog

from celery import shared_task

log = structlog.get_logger(__name__)


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.billing.tasks.handle_stripe_event",
    bind=True,
    max_retries=5,
    default_retry_delay=30,
)
def handle_stripe_event(
    self: Any, event_id: str, event_type: str, event_data: dict[str, Any]
) -> str:
    """Process a Stripe webhook event asynchronously."""
    from services.billing.billing_service import BillingService

    try:
        BillingService.process_event(event_type, event_data)
    except Exception as exc:
        log.exception("billing.task_failed", event_id=event_id, event_type=event_type)
        raise self.retry(exc=exc) from exc

    return f"stripe_event:processed:{event_id}"


@shared_task(  # type: ignore[untyped-decorator]
    name="apps.billing.tasks.send_dunning_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_dunning_email(self: Any, tenant_id: str) -> str:
    """Send a payment-failed notification to the tenant owner."""
    from django.conf import settings
    from django.core.mail import send_mail

    from apps.rbac.models import RoleChoices, UserTenantRole
    from apps.tenants.models import Tenant

    try:
        tenant = Tenant.objects.get(pk=tenant_id)
        owner_role = (
            UserTenantRole.objects.filter(tenant=tenant, role=RoleChoices.OWNER)
            .select_related("user")
            .first()
        )
        if owner_role is None:
            return f"dunning:no_owner:{tenant_id}"

        send_mail(
            subject="Action required: Payment failed for your subscription",
            message=(
                f"Hi {owner_role.user.get_full_name() or owner_role.user.username},\n\n"
                "Your recent payment failed. Please update your payment method to avoid "
                "service interruption.\n\n"
                "You have a 7-day grace period before access is suspended."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner_role.user.email],
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc) from exc

    return f"dunning:sent:{tenant_id}"
