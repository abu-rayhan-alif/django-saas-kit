"""Readiness checks for /health/ (database + Redis)."""

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
