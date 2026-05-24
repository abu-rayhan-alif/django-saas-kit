"""WebSocket consumer for real-time notifications."""

from __future__ import annotations

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket endpoint: ``ws/notifications/``

    Lifecycle
    ---------
    * Connect: authenticate via JWT (handled by JWTAuthMiddlewareStack),
      join the user's personal group ``notifications_<pk>``.
    * Receive group message: forward to the connected client as JSON.
    * Disconnect: leave the group.

    Client receives JSON::

        {
            "id":         "<uuid>",
            "title":      "...",
            "body":       "...",
            "created_at": "2026-01-01T00:00:00+00:00"
        }
    """

    async def connect(self) -> None:
        user = self.scope.get("user")

        if user is None or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.group_name = f"notifications_{user.pk}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.debug("WS connected: user=%s group=%s", user.pk, self.group_name)

    async def disconnect(self, close_code: int) -> None:
        group = getattr(self, "group_name", None)
        if group:
            await self.channel_layer.group_discard(group, self.channel_name)

    # Called by group_send with type "notification.message"
    async def notification_message(self, event: dict) -> None:
        await self.send(
            text_data=json.dumps(
                {
                    "id": event["id"],
                    "title": event["title"],
                    "body": event["body"],
                    "created_at": event["created_at"],
                }
            )
        )
