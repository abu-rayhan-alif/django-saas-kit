"""Tests for DemoSeedService."""

from __future__ import annotations

import pytest
from apps.tenants.models import Domain, Tenant
from examples.demo_config import DEMO_ADMIN, TENANT1_ID, TENANT2_ID
from services.demo.seed_service import DemoSeedService
from services.rbac import RBACService

pytestmark = pytest.mark.django_db


def test_seed_creates_tenants_domains_and_admin():
    result = DemoSeedService.seed()

    assert len(result.tenants) == 2
    assert Tenant.objects.filter(pk=TENANT1_ID).exists()
    assert Tenant.objects.filter(pk=TENANT2_ID).exists()
    assert Domain.objects.filter(domain="tenant1.localhost").exists()
    assert Domain.objects.filter(domain="tenant2.localhost").exists()
    assert result.admin_user.check_password(DEMO_ADMIN.password)
    assert RBACService.get_role(result.admin_user, result.tenants[0]) == "admin"


def test_seed_is_idempotent():
    DemoSeedService.seed()
    DemoSeedService.seed()

    assert Tenant.objects.filter(pk__in=[TENANT1_ID, TENANT2_ID]).count() == 2
    assert Domain.objects.filter(domain__in=["tenant1.localhost", "tenant2.localhost"]).count() == 2
