"""
Unit tests for RBACService.

These tests exercise the service layer directly without touching HTTP.
Key concern: roles are strictly scoped to a tenant — a role in tenant A
must not bleed into tenant B.
"""

import pytest
from apps.rbac.models import RoleChoices, UserTenantRole
from apps.tenants.models import Tenant
from django.contrib.auth.models import User
from services.exceptions import ValidationServiceError
from services.rbac import RBACService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant_a(db):
    return Tenant.objects.create(name="Acme Corp", slug="acme", schema_name="acme")


@pytest.fixture
def tenant_b(db):
    return Tenant.objects.create(name="Globex Corp", slug="globex", schema_name="globex")


@pytest.fixture
def user(db):
    return User.objects.create_user(username="alice", password="Pass1234!")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="bob", password="Pass1234!")


# ---------------------------------------------------------------------------
# assign_role
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAssignRole:
    def test_assign_creates_role(self, user, tenant_a):
        role = RBACService.assign_role(user, tenant_a, RoleChoices.MEMBER)
        assert role.user == user
        assert role.tenant == tenant_a
        assert role.role == RoleChoices.MEMBER

    def test_assign_updates_existing_role(self, user, tenant_a):
        RBACService.assign_role(user, tenant_a, RoleChoices.MEMBER)
        updated = RBACService.assign_role(user, tenant_a, RoleChoices.ADMIN)
        assert updated.role == RoleChoices.ADMIN
        # Still only one row
        assert UserTenantRole.objects.filter(user=user, tenant=tenant_a).count() == 1

    def test_assign_invalid_role_raises(self, user, tenant_a):
        with pytest.raises(ValidationServiceError, match="Invalid role"):
            RBACService.assign_role(user, tenant_a, "superuser")

    def test_assign_records_assigned_by(self, user, other_user, tenant_a):
        role = RBACService.assign_role(user, tenant_a, RoleChoices.MEMBER, assigned_by=other_user)
        assert role.assigned_by == other_user


# ---------------------------------------------------------------------------
# revoke_role
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRevokeRole:
    def test_revoke_existing_role_returns_true(self, user, tenant_a):
        RBACService.assign_role(user, tenant_a, RoleChoices.MEMBER)
        assert RBACService.revoke_role(user, tenant_a) is True
        assert UserTenantRole.objects.filter(user=user, tenant=tenant_a).count() == 0

    def test_revoke_nonexistent_role_returns_false(self, user, tenant_a):
        assert RBACService.revoke_role(user, tenant_a) is False


# ---------------------------------------------------------------------------
# get_role
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGetRole:
    def test_returns_role_string(self, user, tenant_a):
        RBACService.assign_role(user, tenant_a, RoleChoices.OWNER)
        assert RBACService.get_role(user, tenant_a) == RoleChoices.OWNER

    def test_returns_none_when_no_role(self, user, tenant_a):
        assert RBACService.get_role(user, tenant_a) is None


# ---------------------------------------------------------------------------
# has_role — core permission checks
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHasRole:
    def test_returns_true_for_exact_role_match(self, user, tenant_a):
        RBACService.assign_role(user, tenant_a, RoleChoices.ADMIN)
        assert RBACService.has_role(user, tenant_a, [RoleChoices.ADMIN]) is True

    def test_returns_true_when_role_in_list(self, user, tenant_a):
        RBACService.assign_role(user, tenant_a, RoleChoices.OWNER)
        assert RBACService.has_role(user, tenant_a, [RoleChoices.ADMIN, RoleChoices.OWNER]) is True

    def test_returns_false_for_wrong_role(self, user, tenant_a):
        RBACService.assign_role(user, tenant_a, RoleChoices.MEMBER)
        assert RBACService.has_role(user, tenant_a, [RoleChoices.ADMIN]) is False

    def test_returns_false_with_no_role(self, user, tenant_a):
        assert RBACService.has_role(user, tenant_a, [RoleChoices.ADMIN]) is False

    def test_returns_false_for_none_user(self, tenant_a):
        assert RBACService.has_role(None, tenant_a, [RoleChoices.MEMBER]) is False

    def test_returns_false_for_unauthenticated_user(self, tenant_a):
        from unittest.mock import Mock

        anon = Mock(is_authenticated=False)
        assert RBACService.has_role(anon, tenant_a, [RoleChoices.MEMBER]) is False

    # ---- Tenant isolation (the critical invariant) ----

    def test_role_in_tenant_a_does_not_apply_to_tenant_b(self, user, tenant_a, tenant_b):
        """A role granted in tenant A must NOT grant access in tenant B."""
        RBACService.assign_role(user, tenant_a, RoleChoices.OWNER)

        # Confirm access in tenant A
        assert RBACService.has_role(user, tenant_a, [RoleChoices.OWNER]) is True
        # Must be denied in tenant B where no role exists
        assert RBACService.has_role(user, tenant_b, [RoleChoices.OWNER]) is False

    def test_different_roles_in_different_tenants(self, user, tenant_a, tenant_b):
        """User can have different roles in different tenants independently."""
        RBACService.assign_role(user, tenant_a, RoleChoices.OWNER)
        RBACService.assign_role(user, tenant_b, RoleChoices.MEMBER)

        assert RBACService.get_role(user, tenant_a) == RoleChoices.OWNER
        assert RBACService.get_role(user, tenant_b) == RoleChoices.MEMBER

        # Admin check is True in A (owner >= admin conceptually, but has_role
        # does exact membership — owner is NOT in [admin])
        assert RBACService.has_role(user, tenant_a, [RoleChoices.ADMIN]) is False
