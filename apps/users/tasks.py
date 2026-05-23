"""Celery tasks for the users app."""

from services.common.idempotency import IdempotencyService
from services.users.welcome_email_service import WelcomeEmailService

from apps.common.celery_policy import TASK_RETRY_DECORATOR_KWARGS
from celery import shared_task

TASK_NAME = "welcome_email"


@shared_task(name="apps.users.tasks.send_welcome_email", **TASK_RETRY_DECORATOR_KWARGS)
def send_welcome_email(self, user_id: int) -> str:
    """
    Send a welcome email after registration.

    Usage::

        send_welcome_email.delay(user.pk)

    Retries: max 3 with exponential backoff (see ``docs/background-jobs.md``).
    Idempotency key: ``welcome_email:{user_id}``.
    """
    idempotency_key = IdempotencyService.build_key(TASK_NAME, user_id)

    return IdempotencyService.run(
        idempotency_key,
        lambda: WelcomeEmailService.send_to_user(user_id),
    )
