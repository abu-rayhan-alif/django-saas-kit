"""Unit tests for NotificationService."""

from __future__ import annotations

import pytest
from apps.notifications.models import Notification
from django.contrib.auth import get_user_model
from services.exceptions import ValidationServiceError
from services.notifications import NotificationService

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="alice",
        email="alice@example.com",
        password="pass",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="bob",
        email="bob@example.com",
        password="pass",
    )


@pytest.fixture(autouse=True)
def no_channel_layer(settings):
    """Replace channel layer with InMemoryChannelLayer to avoid Redis."""
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }


# ---------------------------------------------------------------------------
# NotificationService.create()
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNotificationServiceCreate:
    def test_creates_notification_in_db(self, user):
        n = NotificationService.create(user, title="Hello", body="World")

        assert n.pk is not None
        assert Notification.objects.filter(pk=n.pk).exists()

    def test_notification_is_unread_by_default(self, user):
        n = NotificationService.create(user, title="Hi", body="There")

        assert n.is_read is False

    def test_notification_belongs_to_correct_user(self, user):
        n = NotificationService.create(user, title="Hi", body="There")

        assert n.user_id == user.pk

    def test_notification_stores_title_and_body(self, user):
        n = NotificationService.create(user, title="My Title", body="My Body")

        assert n.title == "My Title"
        assert n.body == "My Body"


# ---------------------------------------------------------------------------
# NotificationService.mark_read()
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNotificationServiceMarkRead:
    def test_mark_read_flips_is_read(self, user):
        n = NotificationService.create(user, title="T", body="B")

        updated = NotificationService.mark_read(str(n.pk), user)

        assert updated.is_read is True
        assert Notification.objects.get(pk=n.pk).is_read is True

    def test_mark_read_is_idempotent(self, user):
        n = NotificationService.create(user, title="T", body="B")
        NotificationService.mark_read(str(n.pk), user)
        # Second call should not raise
        result = NotificationService.mark_read(str(n.pk), user)
        assert result.is_read is True

    def test_mark_read_wrong_user_raises(self, user, other_user):
        n = NotificationService.create(user, title="T", body="B")

        with pytest.raises(ValidationServiceError):
            NotificationService.mark_read(str(n.pk), other_user)

    def test_mark_read_nonexistent_raises(self, user):
        import uuid

        with pytest.raises(ValidationServiceError):
            NotificationService.mark_read(str(uuid.uuid4()), user)


# ---------------------------------------------------------------------------
# NotificationService.list_unread()
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNotificationServiceListUnread:
    def test_returns_only_unread(self, user):
        n1 = NotificationService.create(user, title="Unread", body="")
        n2 = NotificationService.create(user, title="Read", body="")
        NotificationService.mark_read(str(n2.pk), user)

        unread = list(NotificationService.list_unread(user))

        assert n1 in unread
        assert n2 not in unread

    def test_does_not_include_other_users_notifications(self, user, other_user):
        NotificationService.create(other_user, title="Bob's note", body="")
        NotificationService.create(user, title="Alice's note", body="")

        unread = list(NotificationService.list_unread(user))

        titles = [n.title for n in unread]
        assert "Alice's note" in titles
        assert "Bob's note" not in titles

    def test_empty_when_all_read(self, user):
        n = NotificationService.create(user, title="T", body="B")
        NotificationService.mark_read(str(n.pk), user)

        assert list(NotificationService.list_unread(user)) == []
