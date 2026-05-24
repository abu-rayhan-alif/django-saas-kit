"""NotificationService — create, mark read, and query notifications."""

from __future__ import annotations

import logging

from apps.notifications.models import Notification
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.db.models import QuerySet

from services.exceptions import ValidationServiceError

logger = logging.getLogger(__name__)


def _get_channel_layer():
    """Lazily import channel layer to avoid import-time errors in tests."""
    from channels.layers import get_channel_layer

    return get_channel_layer()


def _notification_group(user_pk) -> str:
    """Return the Channels group name for a user's notifications."""
    return f"notifications_{user_pk}"


class NotificationService:
    """Application-level service for the Notification domain."""

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    @staticmethod
    def create(
        user: User,
        title: str,
        body: str,
    ) -> Notification:
        """Create a notification and broadcast it over the user's WS group.

        Args:
            user: The recipient.
            title: Short notification title (≤255 chars).
            body: Full notification body text.

        Returns:
            The saved ``Notification`` instance.
        """
        notification = Notification.objects.create(user=user, title=title, body=body)

        # Push real-time update — swallow channel errors so the HTTP path
        # is never interrupted by a missing broker in dev/CI.
        try:
            channel_layer = _get_channel_layer()
            if channel_layer is not None:
                async_to_sync(channel_layer.group_send)(
                    _notification_group(user.pk),
                    {
                        "type": "notification.message",
                        "id": str(notification.id),
                        "title": notification.title,
                        "body": notification.body,
                        "created_at": notification.created_at.isoformat(),
                    },
                )
        except Exception:  # noqa: BLE001
            logger.warning(
                "Failed to broadcast notification %s via channel layer",
                notification.id,
                exc_info=True,
            )

        return notification

    @staticmethod
    def mark_read(notification_id: str, user: User) -> Notification:
        """Mark a notification as read.

        Args:
            notification_id: UUID of the notification.
            user: Must be the notification's owner.

        Raises:
            ValidationServiceError: If the notification does not exist or
                belongs to a different user.
        """
        try:
            notification = Notification.objects.get(pk=notification_id, user=user)
        except Notification.DoesNotExist as exc:
            raise ValidationServiceError(f"Notification {notification_id} not found.") from exc

        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])

        return notification

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    @staticmethod
    def list_unread(user: User) -> QuerySet[Notification]:
        """Return all unread notifications for *user*, newest first."""
        return Notification.objects.filter(user=user, is_read=False)

    @staticmethod
    def list_all(user: User) -> QuerySet[Notification]:
        """Return all notifications for *user*, newest first."""
        return Notification.objects.filter(user=user)
