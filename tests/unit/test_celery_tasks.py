"""Celery task tests (SAAS-501) — eager mode via conftest."""

import pytest
from apps.authentication.tasks import cleanup_expired_tokens
from apps.users.tasks import send_welcome_email
from config.celery import app
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from services.users import CreateUserInput, UserService

User = get_user_model()


def test_celery_eager_mode_enabled(settings):
    assert settings.CELERY_TASK_ALWAYS_EAGER is True
    assert settings.CELERY_TASK_EAGER_PROPAGATES is True


def test_beat_schedule_includes_token_cleanup():
    assert "cleanup-expired-tokens-daily" in app.conf.beat_schedule
    entry = app.conf.beat_schedule["cleanup-expired-tokens-daily"]
    assert entry["task"] == "apps.authentication.tasks.cleanup_expired_tokens"


@pytest.mark.django_db(transaction=True)
def test_send_welcome_email_task():
    user = User.objects.create_user(
        username="welcome",
        email="welcome@example.com",
        password="SecurePass123!",
    )

    result = send_welcome_email.delay(user.pk)

    assert result.successful()
    assert result.result == f"welcome_sent:{user.pk}"
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
    assert "Welcome" in mail.outbox[0].subject


@pytest.mark.django_db(transaction=True)
def test_create_user_enqueues_welcome_email():
    """transaction=True commits so transaction.on_commit runs the Celery task (eager)."""
    user = UserService.create_user(
        CreateUserInput(
            email="new@example.com",
            username="newuser",
            password="SecurePass123!",
        )
    )

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]


@pytest.mark.django_db
def test_cleanup_expired_tokens_task(mocker):
    mock_flush = mocker.patch(
        "apps.authentication.tasks.call_command",
        return_value=None,
    )

    result = cleanup_expired_tokens.delay()

    assert result.successful()
    assert result.result == "cleanup_expired_tokens:ok"
    mock_flush.assert_called_once_with("flushexpiredtokens", verbosity=0)


@pytest.mark.django_db
def test_sync_beat_schedule_command():
    call_command("sync_beat_schedule")
    call_command("sync_beat_schedule")  # idempotent

    from django_celery_beat.models import PeriodicTask

    task = PeriodicTask.objects.get(name="cleanup-expired-tokens-daily")
    assert task.task == "apps.authentication.tasks.cleanup_expired_tokens"
    assert task.enabled is True
