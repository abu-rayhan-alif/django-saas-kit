"""Celery tasks for invitation emails."""

from __future__ import annotations

import structlog
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

log = structlog.get_logger(__name__)


@shared_task(
    name="apps.invitations.tasks.send_invitation_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_invitation_email(
    self,
    recipient_email: str,
    tenant_name: str,
    invited_by_name: str,
    role: str,
    accept_url: str,
) -> None:
    """Send a tenant invitation email to *recipient_email*."""
    subject = f"You've been invited to join {tenant_name}"
    body = (
        f"Hi,\n\n"
        f"{invited_by_name} has invited you to join {tenant_name} as a {role}.\n\n"
        f"Accept your invitation here (expires in 72 hours):\n"
        f"{accept_url}\n\n"
        f"If you didn't expect this invitation you can safely ignore this email.\n"
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        log.info("invitation.email_sent", recipient=recipient_email, tenant=tenant_name)
    except Exception as exc:  # noqa: BLE001
        log.warning("invitation.email_failed", recipient=recipient_email, exc=str(exc))
        raise self.retry(exc=exc)
