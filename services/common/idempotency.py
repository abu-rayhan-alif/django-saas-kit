"""Idempotent task execution using the Django cache backend."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from django.core.cache import cache

T = TypeVar("T")

DEFAULT_TTL_SECONDS = 60 * 60 * 24  # 24 hours


class IdempotencyService:
    """
    Prevent duplicate side effects when Celery retries or producers double-enqueue.

    Key pattern: ``{task_name}:{business_id}`` (e.g. ``welcome_email:42``).
    """

    KEY_PREFIX = "celery:idempotent"

    @staticmethod
    def build_key(task_name: str, business_id: str | int) -> str:
        return f"{task_name}:{business_id}"

    @staticmethod
    def cache_key(idempotency_key: str) -> str:
        return f"{IdempotencyService.KEY_PREFIX}:{idempotency_key}"

    @staticmethod
    def run(
        idempotency_key: str,
        operation: Callable[[], T],
        *,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> T:
        """
        Run *operation* at most once per *idempotency_key* within *ttl_seconds*.

        Returns the cached result on duplicate delivery without calling *operation* again.
        """
        full_key = IdempotencyService.cache_key(idempotency_key)

        cached = cache.get(full_key)
        if cached is not None:
            return cached

        result = operation()
        cache.set(full_key, result, timeout=ttl_seconds)
        return result
