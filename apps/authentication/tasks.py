"""Celery tasks for authentication maintenance."""

from django.core.management import call_command

from celery import shared_task


@shared_task(name="apps.authentication.tasks.cleanup_expired_tokens")
def cleanup_expired_tokens() -> str:
    """Remove expired JWT refresh tokens from the blacklist table.

    Scheduled daily via Celery Beat (see ``config/celery.py``).
    """
    call_command("flushexpiredtokens", verbosity=0)
    return "cleanup_expired_tokens:ok"
