"""
Sentry SDK initialization (SAAS-603).

Initializes only when ``SENTRY_DSN`` is set; otherwise returns without error.
"""

from __future__ import annotations

from typing import Any

import structlog
from config.env import get_str


def _before_send(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any] | None:
    """Attach structlog correlation IDs to Sentry events."""
    ctx = structlog.contextvars.get_contextvars()
    tags = event.setdefault("tags", {})
    if request_id := ctx.get("request_id"):
        tags["request_id"] = request_id
    if trace_id := ctx.get("trace_id"):
        tags["trace_id"] = trace_id
    return event


def init_sentry() -> bool:
    """
    Configure Sentry when ``SENTRY_DSN`` is present.

    Returns ``True`` if the SDK was initialized, ``False`` if skipped (no DSN).
    """
    dsn = get_str("SENTRY_DSN", default="").strip()
    if not dsn:
        return False

    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    environment = get_str("SENTRY_ENVIRONMENT", default="production").strip() or "production"
    release = get_str("SENTRY_RELEASE", default="").strip() or None
    traces_sample_rate = float(get_str("SENTRY_TRACES_SAMPLE_RATE", default="0.0"))

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=traces_sample_rate,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        send_default_pii=False,
        before_send=_before_send,
    )
    return True
