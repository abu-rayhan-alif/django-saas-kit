"""Integration tests: two-tenant subdomain isolation (SAAS-T01f).

Verifies that:
  - tenant1.localhost resolves to Tenant 1 only
  - tenant2.localhost resolves to Tenant 2 only
  - Tenants cannot observe each other's data through the middleware layer
  - TenantService.create_tenant() creates tenant + domain atomically
"""

from __future__ import annotations

import json

import pytest
from django.test import Client

from apps.tenants.models import Domain, Tenant
from services.tenants import TenantService
from services.exceptions import ConflictServiceError, ValidationServiceError

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _client_for(domain: str) -> Client:
    """Return a test Client that sends all requests with the given Host header."""
    return Client(SERVER_NAME=domain, HTTP_HOST=domain)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tenant1():
    t = Tenant.objects.create(name="Tenant One", slug="tenant1", schema_name="tenant1")
    Domain.objects.create(tenant=t, domain="tenant1.localhost", is_primary=True)
    return t


@pytest.fixture()
def tenant2():
    t = Tenant.objects.create(name="Tenant Two", slug="tenant2", schema_name="tenant2")
    Domain.objects.create(tenant=t, domain="tenant2.localhost", is_primary=True)
    return t


# ---------------------------------------------------------------------------
# Core isolation
# ---------------------------------------------------------------------------


def test_tenant1_request_resolves_to_tenant1(tenant1, tenant2):
    """A request to tenant1.localhost must set request.tenant to tenant1."""
    from django.test import RequestFactory

    from apps.tenants.middleware import TenantMiddleware

    rf = RequestFactory()
    request = rf.get("/api/v1/", SERVER_NAME="tenant1.localhost")
    request.META["HTTP_HOST"] = "tenant1.localhost"

    captured = {}

    def _capture(req):
        captured["tenant"] = req.tenant
        from django.http import HttpResponse
        return HttpResponse()

    TenantMiddleware(_capture)(request)
    assert captured["tenant"].pk == tenant1.pk
    assert captured["tenant"].pk != tenant2.pk


def test_tenant2_request_resolves_to_tenant2(tenant1, tenant2):
    from django.test import RequestFactory

    from apps.tenants.middleware import TenantMiddleware

    rf = RequestFactory()
    request = rf.get("/api/v1/", SERVER_NAME="tenant2.localhost")
    request.META["HTTP_HOST"] = "tenant2.localhost"

    captured = {}

    def _capture(req):
        captured["tenant"] = req.tenant
        from django.http import HttpResponse
        return HttpResponse()

    TenantMiddleware(_capture)(request)
    assert captured["tenant"].pk == tenant2.pk
    assert captured["tenant"].pk != tenant1.pk


def test_two_tenants_coexist_independently(tenant1, tenant2):
    """Both tenants exist in the DB and each maps to exactly one domain."""
    assert Tenant.objects.count() >= 2
    assert Domain.objects.filter(tenant=tenant1).count() == 1
    assert Domain.objects.filter(tenant=tenant2).count() == 1

    d1 = Domain.objects.get(tenant=tenant1)
    d2 = Domain.objects.get(tenant=tenant2)
    assert d1.domain != d2.domain


def test_tenant_cross_contamination_impossible(tenant1, tenant2):
    """Domain lookup never returns the wrong tenant."""
    d1 = Domain.objects.select_related("tenant").get(domain="tenant1.localhost")
    d2 = Domain.objects.select_related("tenant").get(domain="tenant2.localhost")

    assert d1.tenant.pk != d2.tenant.pk
    assert d1.tenant.pk == tenant1.pk
    assert d2.tenant.pk == tenant2.pk


# ---------------------------------------------------------------------------
# TenantService.create_tenant()
# ---------------------------------------------------------------------------


def test_create_tenant_produces_tenant_and_domain():
    result = TenantService.create_tenant(
        name="Bravo Corp",
        schema_name="bravo",
        domain="bravo.localhost",
    )

    assert result.tenant.name == "Bravo Corp"
    assert result.tenant.schema_name == "bravo"
    assert result.domain.domain == "bravo.localhost"
    assert result.domain.is_primary is True
    assert result.domain.tenant.pk == result.tenant.pk


def test_create_tenant_is_atomic_on_duplicate_domain(db):
    """If domain is already taken the whole operation must roll back."""
    Domain.objects.create(
        tenant=Tenant.objects.create(name="X", slug="x", schema_name="x"),
        domain="taken.localhost",
    )

    with pytest.raises(ConflictServiceError):
        TenantService.create_tenant(
            name="Y", schema_name="y", domain="taken.localhost"
        )

    # Tenant "Y" must NOT have been created
    assert not Tenant.objects.filter(schema_name="y").exists()


def test_create_tenant_rejects_duplicate_schema_name():
    TenantService.create_tenant(name="Alpha", schema_name="alpha", domain="alpha.localhost")

    with pytest.raises(ConflictServiceError, match="schema_name"):
        TenantService.create_tenant(name="Alpha 2", schema_name="alpha", domain="alpha2.localhost")


def test_create_tenant_rejects_invalid_schema_name():
    with pytest.raises(ValidationServiceError):
        TenantService.create_tenant(
            name="Bad", schema_name="invalid slug!", domain="bad.localhost"
        )


# ---------------------------------------------------------------------------
# HTTP smoke — health endpoint visible on any host
# ---------------------------------------------------------------------------


def test_health_endpoint_exempt_from_tenant_resolution():
    """GET /health/ must return 200 even for an unregistered host."""
    client = _client_for("unknown.localhost")
    response = client.get("/health/")
    assert response.status_code == 200


def test_api_endpoint_returns_404_for_unknown_host():
    """An unregistered host hitting an API path gets 404 from the middleware."""
    client = _client_for("ghost.localhost")
    response = client.get("/api/v1/auth/token/", content_type="application/json")
    body = json.loads(response.content)
    assert response.status_code == 404
    assert body["error"] == "not_found"
