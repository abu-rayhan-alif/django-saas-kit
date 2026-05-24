"""Tests for GDPRService — right-to-erasure (NEW-06)."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from services.users.gdpr_service import GDPRService

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(**kwargs):
    defaults = {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "SecurePass123!",
        "first_name": "Test",
        "last_name": "User",
    }
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


# ---------------------------------------------------------------------------
# anonymize mode
# ---------------------------------------------------------------------------


def test_anonymize_clears_pii():
    user = _make_user()
    original_pk = user.pk

    GDPRService.anonymize(user)

    user.refresh_from_db()
    assert user.pk == original_pk, "User row must be kept"
    assert user.username.startswith("deleted_")
    assert user.email.endswith("@deleted.invalid")
    assert user.first_name == ""
    assert user.last_name == ""
    assert not user.is_active
    assert not user.has_usable_password()


def test_anonymize_returns_correct_mode():
    user = _make_user(username="u1", email="u1@example.com")
    result = GDPRService.anonymize(user)
    assert result.mode == "anonymize"
    assert result.user_id == user.pk


def test_anonymize_deletes_notifications():
    from apps.notifications.models import Notification

    user = _make_user(username="u2", email="u2@example.com")
    Notification.objects.create(user=user, title="Hello", body="World")
    Notification.objects.create(user=user, title="Alert", body="Something happened")

    result = GDPRService.anonymize(user)

    assert result.notifications_deleted == 2
    assert Notification.objects.filter(user=user).count() == 0


def test_anonymize_deletes_tenant_roles():
    from apps.rbac.models import UserTenantRole
    from apps.tenants.models import Tenant

    user = _make_user(username="u3", email="u3@example.com")
    tenant = Tenant.objects.create(name="ACME", slug="acme")
    UserTenantRole.objects.create(user=user, tenant=tenant, role="member")

    result = GDPRService.anonymize(user)

    assert result.roles_deleted == 1
    assert UserTenantRole.objects.filter(user=user).count() == 0


def test_anonymize_preserves_other_users():
    user_a = _make_user(username="ua", email="ua@example.com")
    user_b = _make_user(username="ub", email="ub@example.com")

    GDPRService.anonymize(user_a)

    user_b.refresh_from_db()
    assert user_b.email == "ub@example.com"
    assert user_b.is_active


# ---------------------------------------------------------------------------
# hard_delete mode
# ---------------------------------------------------------------------------


def test_hard_delete_removes_user_row():
    user = _make_user(username="hd1", email="hd1@example.com")
    user_pk = user.pk

    result = GDPRService.hard_delete(user)

    assert not User.objects.filter(pk=user_pk).exists()
    assert result.mode == "hard_delete"
    assert result.user_id == user_pk


def test_hard_delete_removes_notifications():
    from apps.notifications.models import Notification

    user = _make_user(username="hd2", email="hd2@example.com")
    Notification.objects.create(user=user, title="Bye", body="Deleted")

    result = GDPRService.hard_delete(user)

    assert result.notifications_deleted == 1
    assert Notification.objects.filter(user_id=result.user_id).count() == 0


def test_hard_delete_removes_roles():
    from apps.rbac.models import UserTenantRole
    from apps.tenants.models import Tenant

    user = _make_user(username="hd3", email="hd3@example.com")
    tenant = Tenant.objects.create(name="Beta", slug="beta")
    UserTenantRole.objects.create(user=user, tenant=tenant, role="admin")

    result = GDPRService.hard_delete(user)

    assert result.roles_deleted == 1
    assert UserTenantRole.objects.filter(user_id=result.user_id).count() == 0


def test_hard_delete_nullifies_assigned_by():
    """assigned_by FK on UserTenantRole uses SET_NULL — must not break."""
    from apps.rbac.models import UserTenantRole
    from apps.tenants.models import Tenant

    admin = _make_user(username="adm", email="adm@example.com")
    member = _make_user(username="mem", email="mem@example.com")
    tenant = Tenant.objects.create(name="Gamma", slug="gamma")
    role = UserTenantRole.objects.create(
        user=member, tenant=tenant, role="member", assigned_by=admin
    )

    GDPRService.hard_delete(admin)

    role.refresh_from_db()
    assert role.assigned_by is None


# ---------------------------------------------------------------------------
# Management command (smoke test)
# ---------------------------------------------------------------------------


def test_delete_user_data_command_anonymize(capsys):
    from io import StringIO

    from django.core.management import call_command

    user = _make_user(username="cmd1", email="cmd1@example.com")

    out = StringIO()
    call_command("delete_user_data", str(user.pk), "--no-input", stdout=out)

    user.refresh_from_db()
    assert user.username.startswith("deleted_")
    assert "Erasure complete" in out.getvalue()


def test_delete_user_data_command_hard_delete(capsys):
    from io import StringIO

    from django.core.management import call_command

    user = _make_user(username="cmd2", email="cmd2@example.com")
    user_pk = user.pk

    out = StringIO()
    call_command("delete_user_data", str(user_pk), "--hard-delete", "--no-input", stdout=out)

    assert not User.objects.filter(pk=user_pk).exists()
    assert "Erasure complete" in out.getvalue()


def test_delete_user_data_command_unknown_user():
    from io import StringIO

    from django.core.management import call_command
    from django.core.management.base import CommandError

    with pytest.raises(CommandError, match="No user found"):
        call_command("delete_user_data", "99999999", "--no-input", stdout=StringIO())
