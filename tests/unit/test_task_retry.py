"""SAAS-502 — Celery retry policy and idempotency tests."""

import pytest
from apps.common.celery_policy import TASK_MAX_RETRIES
from apps.users.tasks import send_welcome_email
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from services.common.idempotency import IdempotencyService
from services.users.welcome_email_service import WelcomeEmailService

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_idempotency_cache(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
    cache.clear()
    yield
    cache.clear()


def test_retry_policy_constants():
    assert TASK_MAX_RETRIES == 3


@pytest.mark.django_db
def test_send_welcome_email_retries_on_failure_then_succeeds(mocker, settings):
    """Task autoretries on transient errors (max 3 retries)."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    user = User.objects.create_user(
        username="retry_user",
        email="retry@example.com",
        password="SecurePass123!",
    )
    attempts = {"count": 0}

    def flaky_send(user_id: int) -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ConnectionError("SMTP temporarily unavailable")
        return WelcomeEmailService.send_to_user(user_id)

    mocker.patch(
        "services.common.idempotency.IdempotencyService.run",
        side_effect=lambda _key, operation, **kwargs: operation(),
    )
    mocker.patch(
        "services.users.welcome_email_service.WelcomeEmailService.send_to_user",
        side_effect=flaky_send,
    )

    result = send_welcome_email.apply(args=[user.pk])

    assert result.successful()
    assert attempts["count"] == 3
    assert result.result == f"welcome_sent:{user.pk}"


@pytest.mark.django_db
def test_send_welcome_email_exhausts_retries_and_fails(mocker, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    user = User.objects.create_user(
        username="fail_user",
        email="fail@example.com",
        password="SecurePass123!",
    )

    mocker.patch(
        "services.common.idempotency.IdempotencyService.run",
        side_effect=lambda _key, operation, **kwargs: operation(),
    )
    mocker.patch(
        "services.users.welcome_email_service.WelcomeEmailService.send_to_user",
        side_effect=ConnectionError("permanent outage"),
    )

    with pytest.raises(ConnectionError, match="permanent outage"):
        send_welcome_email.apply(args=[user.pk])


@pytest.mark.django_db
def test_idempotency_skips_duplicate_side_effect(mocker):
    user = User.objects.create_user(
        username="idem_user",
        email="idem@example.com",
        password="SecurePass123!",
    )
    send_mock = mocker.patch(
        "services.users.welcome_email_service.WelcomeEmailService.send_to_user",
        return_value=f"welcome_sent:{user.pk}",
    )

    key = IdempotencyService.build_key("welcome_email", user.pk)
    first = IdempotencyService.run(key, lambda: WelcomeEmailService.send_to_user(user.pk))
    second = IdempotencyService.run(key, lambda: WelcomeEmailService.send_to_user(user.pk))

    assert first == second
    send_mock.assert_called_once()


@pytest.mark.django_db
def test_send_welcome_email_task_is_idempotent_on_retry_path(mocker, settings):
    """After a successful run, cache prevents duplicate email on re-delivery."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    user = User.objects.create_user(
        username="cached_user",
        email="cached@example.com",
        password="SecurePass123!",
    )

    result1 = send_welcome_email.apply(args=[user.pk])
    assert result1.successful()
    assert len(mail.outbox) == 1

    result2 = send_welcome_email.apply(args=[user.pk])
    assert result2.successful()
    assert len(mail.outbox) == 1
