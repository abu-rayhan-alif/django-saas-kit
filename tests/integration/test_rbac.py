"""
Integration tests: RBAC endpoint enforcement.

Scenarios verified:
  - No token                    → 401 (Unauthorized)
  - Member tries to assign role → 403 (Forbidden)
  - Admin can assign/revoke     → 201 / 204
  - List roles as member        → 200
  - Role from tenant A denied in tenant B (isolation)
"""

import json

import pytest
from apps.rbac.models import RoleChoices
from apps.tenants.models import Tenant
from django.contrib.auth.models import User
from services.rbac import RBACService

TOKEN_URL = "/api/v1/auth/token/"
ASSIGN_URL = "/api/v1/rbac/{tenant_id}/roles/assign/"
REVOKE_URL = "/api/v1/rbac/{tenant_id}/roles/revoke/"
LIST_URL = "/api/v1/rbac/{tenant_id}/roles/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def post_json(client, url, payload, token=None):
    headers = {}
    if token:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
        **headers,
    )


def get_json(client, url, token=None):
    headers = {}
    if token:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client.get(url, content_type="application/json", **headers)


def login(client, username, password="Pass1234!"):
    resp = post_json(client, TOKEN_URL, {"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return resp.json()["access"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(
        name="Test Corp", slug="test-corp", schema_name="test-corp"
    )


@pytest.fixture
def other_tenant(db):
    return Tenant.objects.create(
        name="Other Corp", slug="other-corp", schema_name="other-corp"
    )


@pytest.fixture
def owner_user(db):
    return User.objects.create_user(username="owner", password="Pass1234!")


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(username="admin_user", password="Pass1234!")


@pytest.fixture
def member_user(db):
    return User.objects.create_user(username="member", password="Pass1234!")


@pytest.fixture
def plain_user(db):
    """A user with no role in any tenant."""
    return User.objects.create_user(username="nobody", password="Pass1234!")


@pytest.fixture
def seeded_tenant(tenant, owner_user, admin_user, member_user):
    """Tenant with pre-assigned roles for all fixture users."""
    RBACService.assign_role(owner_user, tenant, RoleChoices.OWNER)
    RBACService.assign_role(admin_user, tenant, RoleChoices.ADMIN)
    RBACService.assign_role(member_user, tenant, RoleChoices.MEMBER)
    return tenant


# ---------------------------------------------------------------------------
# 401 — No authentication
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUnauthenticatedReturns401:
    def test_assign_without_token_returns_401(self, api_client, tenant):
        resp = post_json(
            api_client,
            ASSIGN_URL.format(tenant_id=tenant.id),
            {"user_id": 1, "role": "member"},
        )
        assert resp.status_code == 401

    def test_revoke_without_token_returns_401(self, api_client, tenant):
        resp = post_json(
            api_client,
            REVOKE_URL.format(tenant_id=tenant.id),
            {"user_id": 1},
        )
        assert resp.status_code == 401

    def test_list_without_token_returns_401(self, api_client, tenant):
        resp = get_json(api_client, LIST_URL.format(tenant_id=tenant.id))
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 403 — Wrong role
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestInsufficientRoleReturns403:
    def test_member_cannot_assign_roles(self, api_client, seeded_tenant, member_user, plain_user):
        token = login(api_client, "member")
        resp = post_json(
            api_client,
            ASSIGN_URL.format(tenant_id=seeded_tenant.id),
            {"user_id": plain_user.pk, "role": "member"},
            token=token,
        )
        assert resp.status_code == 403, resp.json()

    def test_member_cannot_revoke_roles(self, api_client, seeded_tenant, member_user, admin_user):
        token = login(api_client, "member")
        resp = post_json(
            api_client,
            REVOKE_URL.format(tenant_id=seeded_tenant.id),
            {"user_id": admin_user.pk},
            token=token,
        )
        assert resp.status_code == 403

    def test_no_role_in_tenant_returns_403(self, api_client, seeded_tenant, plain_user):
        """User authenticated but has no role in this tenant at all."""
        token = login(api_client, "nobody")
        resp = post_json(
            api_client,
            ASSIGN_URL.format(tenant_id=seeded_tenant.id),
            {"user_id": plain_user.pk, "role": "member"},
            token=token,
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 2xx — Authorised actions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAuthorisedActions:
    def test_admin_can_assign_member_role(self, api_client, seeded_tenant, admin_user, plain_user):
        token = login(api_client, "admin_user")
        resp = post_json(
            api_client,
            ASSIGN_URL.format(tenant_id=seeded_tenant.id),
            {"user_id": plain_user.pk, "role": "member"},
            token=token,
        )
        assert resp.status_code == 201, resp.json()
        assert resp.json()["role"] == "member"

    def test_owner_can_assign_admin_role(self, api_client, seeded_tenant, owner_user, plain_user):
        token = login(api_client, "owner")
        resp = post_json(
            api_client,
            ASSIGN_URL.format(tenant_id=seeded_tenant.id),
            {"user_id": plain_user.pk, "role": "admin"},
            token=token,
        )
        assert resp.status_code == 201, resp.json()
        assert resp.json()["role"] == "admin"

    def test_owner_can_revoke_role(self, api_client, seeded_tenant, owner_user, member_user):
        token = login(api_client, "owner")
        resp = post_json(
            api_client,
            REVOKE_URL.format(tenant_id=seeded_tenant.id),
            {"user_id": member_user.pk},
            token=token,
        )
        assert resp.status_code == 204

    def test_member_can_list_roles(self, api_client, seeded_tenant, member_user):
        token = login(api_client, "member")
        resp = get_json(api_client, LIST_URL.format(tenant_id=seeded_tenant.id), token=token)
        assert resp.status_code == 200
        roles = resp.json()
        assert len(roles) == 3
        role_values = {r["role"] for r in roles}
        assert role_values == {"owner", "admin", "member"}


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTenantIsolation:
    def test_owner_in_tenant_a_denied_in_tenant_b(
        self, api_client, tenant, other_tenant, owner_user, plain_user
    ):
        """
        owner_user is owner of `tenant` but has no role in `other_tenant`.
        The assign endpoint for other_tenant must return 403.
        """
        RBACService.assign_role(owner_user, tenant, RoleChoices.OWNER)
        # No role in other_tenant

        token = login(api_client, "owner")
        resp = post_json(
            api_client,
            f"/api/v1/rbac/{other_tenant.id}/roles/assign/",
            {"user_id": str(owner_user.id), "role": RoleChoices.MEMBER},
            token=token,
        )
        assert resp.status_code == 403, resp.json()
