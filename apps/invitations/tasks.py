"""Celery tasks for invitation emails."""

from __future__ import annotations

import structlog
from django.conf import settings
from django.core.mail import send_mail

from celery import shared_task

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
    """Send a tenant invitation email (HTML + plain text)."""
    from django.template.loader import render_to_string

    subject = f"You've been invited to join {tenant_name}"
    ctx = {
        "tenant_name": tenant_name,
        "invited_by_name": invited_by_name,
        "role": role,
        "accept_url": accept_url,
    }
    html_body = render_to_string("emails/invitation.html", ctx)
    plain_body = (
        f"Hi,\n\n"
        f"{invited_by_name} has invited you to join {tenant_name} as a {role}.\n\n"
        f"Accept your invitation here (expires in 72 hours):\n"
        f"{accept_url}\n\n"
        f"If you didn't expect this invitation you can safely ignore this email.\n"
    )
    try:
        send_mail(
            subject=subject,
            message=plain_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_body,
            fail_silently=False,
        )
        log.info("invitation.email_sent", recipient=recipient_email, tenant=tenant_name)
    except Exception as exc:
        log.warning("invitation.email_failed", recipient=recipient_email, exc=str(exc))
        raise self.retry(exc=exc) from exc
