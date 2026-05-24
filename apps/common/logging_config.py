"""
Structured logging configuration (SAAS-601).

- Dev/local: human-readable console output
- Prod/staging: JSON lines for log aggregators
"""

from __future__ import annotations

import logging
import logging.config
from collections.abc import MutableMapping
from typing import Any

import structlog

# ---------------------------------------------------------------------------
# Sensitive-field redaction (NEW-05)
# ---------------------------------------------------------------------------

#: Fields whose values must never appear in log output.
#: Add new names here — do NOT log passwords, raw tokens, or full emails.
SENSITIVE_FIELDS: frozenset[str] = frozenset(
    {
        "password",
        "new_password",
        "old_password",
        "confirm_password",
        "token",
        "access_token",
        "refresh_token",
        "reset_token",
        "id_token",
        "authorization",
        "email",
        "secret",
        "api_key",
        "secret_key",
        "credit_card",
        "ssn",
    }
)

_REDACTED = "[REDACTED]"


def redact_sensitive_fields(  # noqa: ARG001
    logger: Any, method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Drop sensitive values from the log event dict before rendering."""
    for field in SENSITIVE_FIELDS:
        if field in event_dict:
            event_dict[field] = _REDACTED
    return event_dict


def _safe_add_logger_name(
    logger: Any, method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Like structlog.stdlib.add_logger_name but safe for non-stdlib loggers.

    structlog.stdlib.add_logger_name assumes the underlying logger is a stdlib
    LoggerAdapter with a ``.name`` attribute.  When tests use
    ``structlog.testing.capture_logs``, the underlying logger is a
    ``PrintLogger`` which has no ``.name``.  This wrapper skips silently
    in that case so tests don't raise AttributeError.
    """
    name = getattr(logger, "name", None)
    if name:
        event_dict["logger"] = name
    return event_dict


def shared_processors() -> list[structlog.types.Processor]:
    """Processors applied to both structlog and stdlib log records."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        _safe_add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        redact_sensitive_fields,
    ]


def configure_structlog(*, json_logs: bool) -> None:
    """Configure structlog; call once from ``CommonConfig.ready()``."""
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()
    )
    processors = shared_processors() + [
        structlog.processors.format_exc_info,
        renderer,
    ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logging_config(*, json_logs: bool) -> dict[str, Any]:
    """Django ``LOGGING`` dict using structlog ``ProcessorFormatter``."""
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()
    )
    formatter_name = "json" if json_logs else "console"
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            formatter_name: {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": [
                    structlog.processors.format_exc_info,
                    renderer,
                ],
                "foreign_pre_chain": shared_processors(),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": formatter_name,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "INFO",
        },
    }


def reconfigure_logging(*, json_logs: bool) -> None:
    """Apply structlog + stdlib logging (used on Django startup)."""
    configure_structlog(json_logs=json_logs)
    logging.config.dictConfig(get_logging_config(json_logs=json_logs))
