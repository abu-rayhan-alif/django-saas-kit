"""Subdomain-based tenant identification (SAAS-T01b).

Resolves the current tenant from the request hostname via the Domain table
and stores it on ``request.tenant``.

Flow
----
  request.get_host()
      → strip port
      → Domain.objects.get(domain=host)  →  404 if unknown
      → domain.tenant.is_active          →  403 if inactive
      → request.tenant = tenant

Exempt paths (health checks, admin, OpenAPI) bypass resolution and receive
``request.tenant = None``.
"""

from __future__ import annotations

from collections.abc import Callable

import structlog
from django.http import HttpRequest, HttpResponse, JsonResponse

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
            return self.get_response(request)

        # Strip port suffix (e.g. "tenant1.localhost:8000" → "tenant1.localhost")
        host = request.get_host().split(":")[0]

        from apps.tenants.models import Domain  # noqa: PLC0415 — avoids import-time app registry issue

        try:
            domain_obj = Domain.objects.select_related("tenant").get(domain=host)
        except Domain.DoesNotExist:
            log.warning("tenant.domain_not_found", host=host)
            return _tenant_not_found(host)

        tenant = domain_obj.tenant

        if not tenant.is_active:
            log.warning("tenant.inactive", tenant_id=str(tenant.id))
            return _tenant_inactive()

        request.tenant = tenant  # type: ignore[attr-defined]
        structlog.contextvars.bind_contextvars(tenant_id=str(tenant.id))
        return self.get_response(request)
