import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    A notification belonging to a single user.

    Notifications are created by ``NotificationService.create()`` and
    pushed to the user's WebSocket group in real time via Django Channels.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        status = "read" if self.is_read else "unread"
        return f"[{status}] {self.title} -> {self.user}"
