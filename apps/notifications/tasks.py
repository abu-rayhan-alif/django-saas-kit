"""Celery tasks for the notifications app."""

from __future__ import annotations

from django.conf import settings
from services.common import EmailService
from services.common.idempotency import IdempotencyService

from apps.common.celery_policy import TASK_RETRY_DECORATOR_KWARGS
from celery import shared_task

TASK_NAME = "send_email_notification"


@shared_task(
    name="apps.notifications.tasks.send_email_notification",
    **TASK_RETRY_DECORATOR_KWARGS,
)
def send_email_notification(self, notification_id: str) -> str:
    """Send an email for a persisted Notification.

    Args:
        notification_id: UUID string of the ``Notification`` to email.

    Returns:
        A status string ``"email_notification_sent:<id>"``.

    The task is idempotent: if it has already run successfully for this
    *notification_id* within the idempotency TTL it will be a no-op.
    Retries follow the shared exponential-backoff policy (max 3 retries).

    Usage::

        send_email_notification.delay(str(notification.id))
    """
    from apps.notifications.models import Notification

    idempotency_key = IdempotencyService.build_key(TASK_NAME, notification_id)

    def _send():
        try:
            notification = Notification.objects.select_related("user").get(pk=notification_id)
        except Notification.DoesNotExist:
            # Notification was deleted before the task ran — nothing to do.
            return f"email_notification_skipped:{notification_id}"

        user = notification.user
        context = {
            "user_name": user.get_full_name() or user.username,
            "title": notification.title,
            "body": notification.body,
            "frontend_url": settings.FRONTEND_URL,
        }

        EmailService.send(
            subject=notification.title,
            to=user.email,
            template_html="emails/notification.html",
            template_txt="emails/notification.txt",
            context=context,
        )
        return f"email_notification_sent:{notification_id}"

    return IdempotencyService.run(idempotency_key, _send)
