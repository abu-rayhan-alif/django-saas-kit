"""Integration tests: UserListView must respect tenant boundaries.

Verifies that authenticated users (even admins) cannot see users belonging
to a different tenant through GET /api/v1/users/.
"""

from __future__ import annotations

import json

import pytest
from apps.rbac.models import RoleChoices, UserTenantRole
from apps.tenants.models import Domain, Tenant
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _client_for(domain: str, user=None) -> Client:
    client = Client(SERVER_NAME=domain, HTTP_HOST=domain)
    if user is not None:
        client.force_login(user)
    return client


def _get_users(client: Client, token: str) -> list[dict]:
    resp = client.get(
        "/api/v1/users/",
        HTTP_AUTHORIZATION=f"Bearer {token}",
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.content
    return json.loads(resp.content).get("results", [])


def _obtain_token(domain: str, username: str, password: str) -> str:
    client = Client(SERVER_NAME=domain, HTTP_HOST=domain)
    resp = client.post(
        "/api/v1/auth/token/",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.content
    return json.loads(resp.content)["access"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tenant_a():
    t = Tenant.objects.create(name="Alpha Corp", slug="alpha", schema_name="alpha")
    Domain.objects.create(tenant=t, domain="alpha.localhost", is_primary=True)
    return t


@pytest.fixture()
def tenant_b():
    t = Tenant.objects.create(name="Beta Corp", slug="beta", schema_name="beta")
    Domain.objects.create(tenant=t, domain="beta.localhost", is_primary=True)
    return t


@pytest.fixture()
def admin_user_a(tenant_a):
    user = User.objects.create_superuser(
        username="admin_a", email="admin_a@example.com", password="StrongPass123!"
    )
    UserTenantRole.objects.create(user=user, tenant=tenant_a, role=RoleChoices.OWNER)
    return user


@pytest.fixture()
def member_user_b(tenant_b):
    user = User.objects.create_user(
        username="member_b", email="member_b@example.com", password="StrongPass123!"
    )
    UserTenantRole.objects.create(user=user, tenant=tenant_b, role=RoleChoices.MEMBER)
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_user_list_returns_only_own_tenant_users(tenant_a, tenant_b, admin_user_a, member_user_b):
    """Admin of tenant_a must NOT see member_b who belongs only to tenant_b."""
    token = _obtain_token("alpha.localhost", "admin_a", "StrongPass123!")
    client = Client(SERVER_NAME="alpha.localhost", HTTP_HOST="alpha.localhost")
    results = _get_users(client, token)

    user_ids = {u["id"] for u in results}
    assert str(admin_user_a.pk) in user_ids, "Admin should see their own user"
    assert str(member_user_b.pk) not in user_ids, "Cross-tenant user must NOT appear"


def test_user_list_empty_when_no_tenant_members(tenant_a):
    """Tenant with no role assignments returns empty list."""
    admin = User.objects.create_superuser(
        username="lone_admin", email="lone@example.com", password="StrongPass123!"
    )
    # Admin has no UserTenantRole for tenant_a
    token = _obtain_token("alpha.localhost", "lone_admin", "StrongPass123!")
    client = Client(SERVER_NAME="alpha.localhost", HTTP_HOST="alpha.localhost")
    results = _get_users(client, token)
    assert results == [], f"Expected empty list but got {results}"


def test_unauthenticated_user_list_returns_401(tenant_a):
    client = Client(SERVER_NAME="alpha.localhost", HTTP_HOST="alpha.localhost")
    resp = client.get("/api/v1/users/", content_type="application/json")
    assert resp.status_code == 401
