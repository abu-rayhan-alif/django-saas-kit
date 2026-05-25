"""Subdomain-based tenant identification (SAAS-T01b).

Resolves the current tenant from the request hostname via the Domain table
and stores it on ``request.tenant``.

Flow
----
  request.get_host()
      → strip port
      → Redis cache lookup (TENANT_CACHE_TTL seconds)
      → Domain.objects.get(domain=host)  →  404 if unknown
      → domain.tenant.is_active          →  403 if inactive
      → request.tenant = tenant
      → services.tenant_context.set_tenant_id(tenant.id)

Exempt paths (health checks, admin, OpenAPI) bypass resolution and receive
``request.tenant = None``.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

import structlog
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse

from services.tenant_context import clear_tenant, set_tenant_id

log = structlog.get_logger(__name__)

_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/admin/",
    "/health/",
    "/ready/",
    "/api/schema/",
    "/api/docs/",
    "/api/redoc/",
    "/static/",
)

_TENANT_CACHE_TTL = 300   # 5 minutes
_NEGATIVE_CACHE_TTL = 60  # 1 minute for "not found" entries
_CACHE_SENTINEL = "__not_found__"


def _cache_key(host: str) -> str:
    return f"tenant:domain:{host}"


def _tenant_not_found(host: str) -> JsonResponse:
    return JsonResponse(
        {"error": "not_found", "message": "Tenant not found.", "details": {}},
        status=404,
    )


def _tenant_inactive() -> JsonResponse:
    return JsonResponse(
        {"error": "tenant_inactive", "message": "This tenant is inactive.", "details": {}},
        status=403,
    )


class TenantMiddleware:
    """Identify the current tenant from the request hostname."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if any(request.path.startswith(p) for p in _EXEMPT_PREFIXES):
            request.tenant = None  # type: ignore[attr-defined]
            clear_tenant()
            return self.get_response(request)

        # Strip port suffix (e.g. "tenant1.localhost:8000" → "tenant1.localhost")
        host = request.get_host().split(":")[0]

        tenant = self._resolve_tenant(host)

        if tenant is None:
            return _tenant_not_found(host)

        if not tenant.is_active:
            log.warning("tenant.inactive", tenant_id=str(tenant.id))
            return _tenant_inactive()

        request.tenant = tenant  # type: ignore[attr-defined]
        set_tenant_id(tenant.id)
        structlog.contextvars.bind_contextvars(tenant_id=str(tenant.id))
        response = self.get_response(request)
        clear_tenant()
        return response

    @staticmethod
    def _resolve_tenant(host: str):
        """Resolve tenant from cache or DB. Returns None for unknown hosts."""
        from apps.tenants.models import (
            Domain,  # noqa: PLC0415 — avoids import-time app registry issue
        )

        key = _cache_key(host)
        cached = cache.get(key)

        if cached is _CACHE_SENTINEL or cached == _CACHE_SENTINEL:
            return None

        if cached is not None:
            return cached

        try:
            domain_obj = Domain.objects.select_related("tenant").get(domain=host)
            tenant = domain_obj.tenant
            cache.set(key, tenant, _TENANT_CACHE_TTL)
            return tenant
        except Domain.DoesNotExist:
            log.warning("tenant.domain_not_found", host=host)
            cache.set(key, _CACHE_SENTINEL, _NEGATIVE_CACHE_TTL)
            return None

    @staticmethod
    def invalidate_cache(host: str) -> None:
        """Call this after Domain create/update/delete to bust the cache."""
        cache.delete(_cache_key(host))
