"""Celery tasks for async Stripe webhook processing and dunning."""

from __future__ import annotations

from typing import Any

import structlog

from celery import shared_task

log = structlog.get_logger(__name__)


@shared_task(
    name="apps.billing.tasks.handle_stripe_event",
    bind=True,
    max_retries=5,
    default_retry_delay=30,
)
def handle_stripe_event(self: Any, event_id: str, event_type: str, event_data: dict[str, Any]) -> str:
    """Process a Stripe webhook event asynchronously."""
    from services.billing.billing_service import BillingService

    try:
        BillingService.process_event(event_type, event_data)
    except Exception as exc:
        log.exception("billing.task_failed", event_id=event_id, event_type=event_type)
        raise self.retry(exc=exc) from exc

    return f"stripe_event:processed:{event_id}"


@shared_task(
    name="apps.billing.tasks.send_dunning_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_dunning_email(self: Any, tenant_id: str) -> str:
    """Send a payment-failed notification to the tenant owner (HTML + plain text)."""
    from django.conf import settings
    from django.core.mail import send_mail
    from django.template.loader import render_to_string

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

        user = owner_role.user
        subscription = getattr(tenant, "subscription", None)
        grace_end = (
            subscription.grace_period_end.strftime("%B %d, %Y")
            if subscription and subscription.grace_period_end
            else "soon"
        )
        plan_name = subscription.plan.name if subscription and subscription.plan else "Unknown"
        billing_url = getattr(
            settings,
            "BILLING_PORTAL_URL",
            f"{getattr(settings, 'FRONTEND_URL', '')}/billing",
        )

        ctx = {
            "user_name": user.get_full_name() or user.username,
            "tenant_name": tenant.name,
            "plan_name": plan_name,
            "grace_period_end": grace_end,
            "billing_url": billing_url,
        }
        html_body = render_to_string("emails/payment_failed.html", ctx)
        plain_body = (
            f"Hi {ctx['user_name']},\n\n"
            f"Your recent payment failed for {tenant.name}.\n"
            f"Please update your payment method before {grace_end} to avoid service interruption.\n\n"
            f"Update here: {billing_url}"
        )

        send_mail(
            subject=f"Action required: Payment failed for {tenant.name}",
            message=plain_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_body,
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc) from exc

    return f"dunning:sent:{tenant_id}"


@shared_task(
    name="apps.billing.tasks.send_trial_ending_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_trial_ending_email(self: Any, tenant_id: str, days_remaining: int = 3) -> str:
    """Send a trial-ending reminder to the tenant owner."""
    from django.conf import settings
    from django.core.mail import send_mail
    from django.template.loader import render_to_string

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
            return f"trial_ending:no_owner:{tenant_id}"

        user = owner_role.user
        subscription = getattr(tenant, "subscription", None)
        trial_end = (
            subscription.trial_end.strftime("%B %d, %Y")
            if subscription and subscription.trial_end
            else "soon"
        )
        plan_name = subscription.plan.name if subscription and subscription.plan else "Trial"
        billing_url = getattr(
            settings,
            "BILLING_PORTAL_URL",
            f"{getattr(settings, 'FRONTEND_URL', '')}/billing",
        )

        ctx = {
            "user_name": user.get_full_name() or user.username,
            "tenant_name": tenant.name,
            "plan_name": plan_name,
            "days_remaining": days_remaining,
            "trial_end_date": trial_end,
            "billing_url": billing_url,
        }
        html_body = render_to_string("emails/trial_ending.html", ctx)
        plain_body = (
            f"Hi {ctx['user_name']},\n\n"
            f"Your free trial for {tenant.name} ends in {days_remaining} day(s) on {trial_end}.\n"
            f"Add a payment method here to continue: {billing_url}"
        )

        send_mail(
            subject=f"Your trial ends in {days_remaining} day(s) — {tenant.name}",
            message=plain_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_body,
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc) from exc

    return f"trial_ending:sent:{tenant_id}"
