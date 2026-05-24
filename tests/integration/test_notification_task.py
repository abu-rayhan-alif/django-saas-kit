"""
Integration test: send_email_notification Celery task (SAAS-902).

Runs the task synchronously (CELERY_TASK_ALWAYS_EAGER=True is set in the
root conftest) and verifies that a real email is placed in Django's locmem
outbox with the correct params.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core import mail

from apps.notifications.models import Notification
from apps.notifications.tasks import send_email_notification
from services.notifications import NotificationService

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="carol",
        email="carol@example.com",
        password="pass",
        first_name="Carol",
    )


@pytest.fixture(autouse=True)
def locmem_email(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture(autouse=True)
def no_channel_layer(settings):
    settings.CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_send_email_notification_delivers_email(user):
    """Task sends exactly one email with the notification title as subject."""
    notification = NotificationService.create(user, title="New alert", body="Check this out.")

    result = send_email_notification(str(notification.id))

    assert result == f"email_notification_sent:{notification.id}"
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == "New alert"
    assert msg.to == ["carol@example.com"]


@pytest.mark.django_db
def test_send_email_notification_includes_html_alternative(user):
    """Email must have an HTML alternative (multipart/alternative)."""
    notification = NotificationService.create(user, title="Alert", body="Details here.")

    send_email_notification(str(notification.id))

    html_parts = [c for c, m in mail.outbox[0].alternatives if m == "text/html"]
    assert html_parts, "Expected HTML alternative"
    assert "Details here." in html_parts[0]


@pytest.mark.django_db
def test_send_email_notification_is_idempotent(user):
    """Running the task twice should send only one email."""
    notification = NotificationService.create(user, title="Once", body="Only once.")

    send_email_notification(str(notification.id))
    send_email_notification(str(notification.id))

    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_send_email_notification_skips_deleted_notification(user):
    """If the notification was deleted before the task runs, no email is sent."""
    notification = NotificationService.create(user, title="Gone", body="Deleted.")
    nid = str(notification.id)
    Notification.objects.filter(pk=nid).delete()

    result = send_email_notification(nid)

    assert result == f"email_notification_skipped:{nid}"
    assert len(mail.outbox) == 0
