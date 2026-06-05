"""Unit tests for FeatureService flag resolution."""

from __future__ import annotations

import pytest
from django.test import override_settings
from services.features import FeatureService

pytestmark = pytest.mark.django_db


@pytest.fixture()
def tenant():
    from apps.tenants.models import Tenant

    return Tenant.objects.create(name="Flag Co", slug="flagco", schema_name="flagco")


def test_is_enabled_returns_settings_default(tenant):
    assert FeatureService.is_enabled("advanced_analytics", tenant=tenant) is False
    assert FeatureService.is_enabled("unknown_flag", tenant=tenant) is False


def test_tenant_override_takes_priority_over_default(tenant):
    FeatureService.set_for_tenant(tenant, "advanced_analytics", is_enabled=True)

    assert FeatureService.is_enabled("advanced_analytics", tenant=tenant) is True


def test_tenant_override_can_force_disable(tenant):
    FeatureService.set_for_tenant(tenant, "api_access", is_enabled=False)

    assert FeatureService.is_enabled("api_access", tenant=tenant) is False


def test_is_enabled_extracts_tenant_from_request(tenant):
    from types import SimpleNamespace

    FeatureService.set_for_tenant(tenant, "bulk_export", is_enabled=True)
    request = SimpleNamespace(tenant=tenant)

    assert FeatureService.is_enabled("bulk_export", request=request) is True


def test_for_tenant_merges_defaults_and_overrides(tenant):
    FeatureService.set_for_tenant(tenant, "advanced_analytics", is_enabled=True)
    FeatureService.set_for_tenant(tenant, "custom_flag", is_enabled=False)

    flags = FeatureService.for_tenant(tenant)

    assert flags["advanced_analytics"] is True
    assert flags["custom_flag"] is False
    assert "api_access" in flags


def test_set_for_tenant_updates_existing_override(tenant):
    FeatureService.set_for_tenant(tenant, "sso", is_enabled=False, note="off")
    FeatureService.set_for_tenant(tenant, "sso", is_enabled=True, note="on")

    from apps.features.models import TenantFeatureFlag

    override = TenantFeatureFlag.objects.get(tenant=tenant, flag_name="sso")
    assert override.is_enabled is True
    assert override.note == "on"


def test_sync_plan_flags_applies_plan_configuration(tenant):
    from apps.billing.models import Plan, Subscription

    plan = Plan.objects.create(slug="pro", name="Pro")
    Subscription.objects.create(
        tenant=tenant,
        plan=plan,
        stripe_customer_id="cus_plan_flags",
    )

    FeatureService.sync_plan_flags(tenant)

    assert FeatureService.is_enabled("advanced_analytics", tenant=tenant) is True
    assert FeatureService.is_enabled("white_label", tenant=tenant) is False


def test_sync_plan_flags_noop_without_subscription(tenant):
    FeatureService.sync_plan_flags(tenant)

    from apps.features.models import TenantFeatureFlag

    assert TenantFeatureFlag.objects.filter(tenant=tenant).count() == 0


@override_settings(PLAN_FEATURE_FLAGS={})
def test_sync_plan_flags_noop_when_setting_empty(tenant):
    from apps.billing.models import Plan, Subscription

    plan = Plan.objects.create(slug="pro", name="Pro")
    Subscription.objects.create(
        tenant=tenant,
        plan=plan,
        stripe_customer_id="cus_empty_plan_flags",
    )

    FeatureService.sync_plan_flags(tenant)

    from apps.features.models import TenantFeatureFlag

    assert TenantFeatureFlag.objects.filter(tenant=tenant).count() == 0


def test_tenant_feature_flag_str(tenant):
    from apps.features.models import TenantFeatureFlag

    flag = TenantFeatureFlag.objects.create(
        tenant=tenant,
        flag_name="beta_ui",
        is_enabled=True,
    )

    assert "beta_ui" in str(flag)
    assert "ON" in str(flag)
