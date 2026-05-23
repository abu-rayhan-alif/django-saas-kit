"""Shared Celery retry policy (SAAS-502)."""

from __future__ import annotations

from typing import Any

# Max 3 retries after the first attempt (4 executions total)
TASK_MAX_RETRIES = 3

# Exponential backoff: 2**retries * base seconds (Celery retry_backoff)
TASK_RETRY_BACKOFF_MAX_SECONDS = 600

TASK_RETRY_DECORATOR_KWARGS: dict[str, Any] = {
    "bind": True,
    "autoretry_for": (Exception,),
    "retry_kwargs": {"max_retries": TASK_MAX_RETRIES},
    "retry_backoff": True,
    "retry_backoff_max": TASK_RETRY_BACKOFF_MAX_SECONDS,
    "retry_jitter": True,
}
