"""Unit tests for TenantMiddleware (SAAS-T01e).

Tests cover:
  - Known active subdomain  → request.tenant is set correctly
  - Unknown subdomain       → 404
  - Inactive tenant         → 403
  - Port stripping          → "tenant1.localhost:8000" resolves correctly
  - Exempt paths            → bypass middleware (request.tenant = None)
"""

from __future__ import annotations

import pytest
from django.test import RequestFactory

from apps.tenants.middleware import TenantMiddleware
from apps.tenants.models import Domain, Tenant

pytestmark = pytest.mark.django_db

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def active_tenant(db):
    tenant = Tenant.objects.create(name="Acme", slug="acme", schema_name="acme")
    Domain.objects.create(tenant=tenant, domain="acme.localhost", is_primary=True)
    return tenant


@pytest.fixture()
def inactive_tenant(db):
    tenant = Tenant.objects.create(
        name="Dormant", slug="dormant", schema_name="dormant", is_active=False
    )
    Domain.objects.create(tenant=tenant, domain="dormant.localhost", is_primary=True)
    return tenant


def _get_response(request):
    """Sentinel view that echoes back request.tenant."""
    from django.http import JsonResponse

    return JsonResponse({"tenant": str(getattr(request, "tenant", None))})


def _make_request(path: str, host: str) -> object:
    rf = RequestFactory()
    request = rf.get(path, SERVER_NAME=host.split(":")[0])
    # Simulate Host header including optional port
    request.META["HTTP_HOST"] = host
    return request


# ---------------------------------------------------------------------------
# Core resolution
# ---------------------------------------------------------------------------


def test_known_subdomain_sets_request_tenant(active_tenant):
    request = _make_request("/api/v1/", "acme.localhost")
    middleware = TenantMiddleware(_get_response)
    middleware(request)

    assert request.tenant == active_tenant


def test_unknown_subdomain_returns_404():
    request = _make_request("/api/v1/", "ghost.localhost")
    middleware = TenantMiddleware(_get_response)
    response = middleware(request)

    assert response.status_code == 404


def test_inactive_tenant_returns_403(inactive_tenant):
    request = _make_request("/api/v1/", "dormant.localhost")
    middleware = TenantMiddleware(_get_response)
    response = middleware(request)

    assert response.status_code == 403


def test_port_is_stripped_from_host(active_tenant):
    """'acme.localhost:8000' must resolve the same as 'acme.localhost'."""
    request = _make_request("/api/v1/", "acme.localhost:8000")
    middleware = TenantMiddleware(_get_response)
    middleware(request)

    assert request.tenant == active_tenant


# ---------------------------------------------------------------------------
# Exempt paths bypass tenant resolution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/health/",
        "/ready/",
        "/admin/",
        "/api/docs/",
        "/api/schema/",
        "/api/redoc/",
        "/static/app.css",
    ],
)
def test_exempt_paths_skip_resolution(path):
    """Exempt paths must not hit the DB and must set request.tenant = None."""
    request = _make_request(path, "unknown-host.localhost")
    middleware = TenantMiddleware(_get_response)
    response = middleware(request)

    # Middleware called get_response (no 404/403 short-circuit)
    assert response.status_code == 200
    assert request.tenant is None


# ---------------------------------------------------------------------------
# Response body shape
# ---------------------------------------------------------------------------


def test_404_response_body():
    import json

    request = _make_request("/api/v1/", "nobody.localhost")
    middleware = TenantMiddleware(_get_response)
    response = middleware(request)

    body = json.loads(response.content)
    assert body["error"] == "not_found"
    assert response.status_code == 404


def test_403_response_body(inactive_tenant):
    import json

    request = _make_request("/api/v1/", "dormant.localhost")
    middleware = TenantMiddleware(_get_response)
    response = middleware(request)

    body = json.loads(response.content)
    assert body["error"] == "tenant_inactive"
    assert response.status_code == 403
