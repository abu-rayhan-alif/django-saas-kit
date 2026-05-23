"""
Structured logging configuration (SAAS-601).

- Dev/local: human-readable console output
- Prod/staging: JSON lines for log aggregators
"""

from __future__ import annotations

import logging
import logging.config
from typing import Any

import structlog


def shared_processors() -> list[structlog.types.Processor]:
    """Processors applied to both structlog and stdlib log records."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
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
