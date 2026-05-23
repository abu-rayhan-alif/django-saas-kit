"""Dependency checks for ``GET /ready/`` (database + Redis)."""

from __future__ import annotations

from django.core.cache import cache
from django.db import connection


def check_database() -> str:
    connection.ensure_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return "ok"


def check_redis() -> str:
    probe_key = "health:redis"
    cache.set(probe_key, "ok", timeout=5)
    if cache.get(probe_key) != "ok":
        return "error"
    cache.delete(probe_key)
    return "ok"


def run_readiness_checks() -> tuple[dict[str, str], bool]:
    """
    Run database and Redis probes.

    Returns ``(checks, all_ok)`` where each check value is ``ok`` or ``error``.
    """
    checks: dict[str, str] = {}

    try:
        checks["database"] = check_database()
    except Exception:
        checks["database"] = "error"

    try:
        checks["redis"] = check_redis()
    except Exception:
        checks["redis"] = "error"

    all_ok = all(value == "ok" for value in checks.values())
    return checks, all_ok
