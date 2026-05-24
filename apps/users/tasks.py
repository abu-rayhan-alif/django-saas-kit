"""Celery tasks for the users app."""

import logging

from services.common.idempotency import IdempotencyService
from services.exceptions import ValidationServiceError
from services.users.welcome_email_service import WelcomeEmailService

from apps.common.celery_policy import TASK_RETRY_DECORATOR_KWARGS
from celery import shared_task

logger = logging.getLogger(__name__)

TASK_NAME = "welcome_email"


@shared_task(name="apps.users.tasks.send_welcome_email", **TASK_RETRY_DECORATOR_KWARGS)
def send_welcome_email(self, user_id: int) -> str:
    """
    Send a welcome email after registration.

    Usage::

        send_welcome_email.delay(user.pk)

    Retries: max 3 with exponential backoff (see docs/background-jobs.md).
    Idempotency key: welcome_email:{user_id}.

    Note: ValidationServiceError (e.g. user not found) is a permanent failure
    and is NOT retried -- retrying would be pointless if the user no longer
    exists.
    """
    idempotency_key = IdempotencyService.build_key(TASK_NAME, user_id)

    def _send():
        try:
            return WelcomeEmailService.send_to_user(user_id)
        except ValidationServiceError as exc:
            # Permanent failure -- user was deleted before the task ran.
            # Log and return a skip result rather than raising (which would
            # trigger the autoretry policy pointlessly).
            logger.warning(
                "send_welcome_email skipped -- user not found: user_id=%s error=%s",
                user_id,
                exc,
            )
            return f"welcome_skipped:{user_id}"

    return IdempotencyService.run(idempotency_key, _send)
