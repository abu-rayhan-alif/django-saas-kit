"""JWT authentication middleware for Django Channels WebSocket connections.

Reads Authorization: Bearer <token> from the WebSocket headers (or a
?token=<jwt> query-string parameter as a fallback) and populates
scope["user"] before the consumer is invoked.

Security note: the query-string fallback is provided for clients that cannot
set custom headers (e.g. browser WebSocket API). Tokens passed via query
string appear in server access logs, so prefer the Authorization header
whenever possible.
"""

from __future__ import annotations

import logging
from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)


@database_sync_to_async
def _get_user_from_token(raw_token: str):
    """Validate an access token and return the corresponding User (or AnonymousUser)."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        token = AccessToken(raw_token)  # type: ignore[arg-type]
        user_id = token["user_id"]
        return User.objects.get(pk=user_id)
    except (InvalidToken, TokenError, User.DoesNotExist):
        return AnonymousUser()


class JWTAuthMiddleware:
    """ASGI middleware that injects a Django User into the Channels scope."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # 1. Try Authorization header (preferred -- tokens are NOT logged)
        raw_token = None
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()
        if auth_header.lower().startswith("bearer "):
            raw_token = auth_header[7:].strip()

        # 2. Fall back to ?token= query string (browser WebSocket API limitation).
        # SECURITY: query-string tokens appear in server access logs.
        # Prefer the Authorization header whenever the client supports it.
        if not raw_token:
            qs = parse_qs(scope.get("query_string", b"").decode())
            tokens = qs.get("token", [])
            if tokens:
                raw_token = tokens[0]
                logger.warning(
                    "WS JWT supplied via query string -- prefer Authorization header "
                    "to avoid token exposure in server access logs. path=%s",
                    scope.get("path", ""),
                )

        scope["user"] = await _get_user_from_token(raw_token) if raw_token else AnonymousUser()

        return await self.inner(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """Wrap *inner* with JWT auth, then fall back to Channels session auth."""
    return JWTAuthMiddleware(AuthMiddlewareStack(inner))
