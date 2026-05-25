"""Celery tasks for authentication maintenance."""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management import call_command
from django.template.loader import render_to_string

from celery import shared_task


@shared_task(name="apps.authentication.tasks.cleanup_expired_tokens")
def cleanup_expired_tokens() -> str:
    """Remove expired JWT refresh tokens from the blacklist table.

    Scheduled daily via Celery Beat (see ``config/celery.py``).
    """
    call_command("flushexpiredtokens", verbosity=0)
    return "cleanup_expired_tokens:ok"


@shared_task(
    name="apps.authentication.tasks.send_password_reset_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_password_reset_email(
    self,
    recipient_email: str,
    user_name: str,
    reset_link: str,
    uid: str,
    token: str,
    hours_valid: int,
) -> str:
    """Send a password-reset email asynchronously with automatic retry on SMTP failure."""
    context = {
        "user_name": user_name,
        "reset_link": reset_link,
        "uid": uid,
        "token": token,
        "hours_valid": hours_valid,
    }
    body = render_to_string("emails/password_reset.txt", context)
    html_body = render_to_string("emails/password_reset.html", context)

    try:
        send_mail(
            subject="Password Reset Request",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
            html_message=html_body,
        )
    except Exception as exc:
        raise self.retry(exc=exc) from exc

    return f"password_reset_email:sent:{recipient_email}"
