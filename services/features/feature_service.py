"""Feature flag service — resolves flag state for a tenant / request.

Resolution order
----------------
1. ``TenantFeatureFlag`` row for the tenant  (highest priority)
2. Global waffle Flag / Switch
3. ``FEATURE_FLAGS_DEFAULTS`` setting
4. False

Example usage::

    from services.features import FeatureService

    # In a view — pass the DRF request:
    if FeatureService.is_enabled("new_dashboard", request=request):
        ...

    # In a service / task — pass tenant directly:
    if FeatureService.is_enabled("bulk_export", tenant=tenant):
        ...

    # Bulk check (returns dict[str, bool]):
    flags = FeatureService.for_tenant(tenant)
    # {"new_dashboard": True, "bulk_export": False, ...}
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rest_framework.request import Request

    from apps.tenants.models import Tenant

log = logging.getLogger(__name__)


def _get_waffle_flag(flag_name: str, request) -> bool | None:
    """Check django-waffle for a Flag or Switch; return None if not found."""
    try:
        import waffle

        # Try Flag first (user/request-aware)
        if request is not None:
            try:
                return waffle.flag_is_active(request, flag_name)
            except Exception:  # noqa: BLE001
                pass

        # Fall back to Switch (global, no request needed)
        try:
            return waffle.switch_is_active(flag_name)
        except Exception:  # noqa: BLE001
            pass
    except ImportError:
        pass
    return None


def _get_default(flag_name: str) -> bool:
    from django.conf import settings

    defaults: dict[str, bool] = getattr(settings, "FEATURE_FLAGS_DEFAULTS", {})
    return defaults.get(flag_name, False)


class FeatureService:
    """Resolve feature flag state for a tenant or request."""

    @staticmethod
    def is_enabled(
        flag_name: str,
        *,
        request: "Request | None" = None,
        tenant: "Tenant | None" = None,
    ) -> bool:
        """
        Return True if *flag_name* is enabled for the given context.

        Pass either ``request`` (preferred — extracts tenant + user automatically)
        or ``tenant`` directly.
        """
        from apps.features.models import TenantFeatureFlag

        resolved_tenant = tenant
        if resolved_tenant is None and request is not None:
            resolved_tenant = getattr(request, "tenant", None)

        # 1. Per-tenant override
        if resolved_tenant is not None:
            try:
                override = TenantFeatureFlag.objects.get(
                    tenant=resolved_tenant, flag_name=flag_name
                )
                return override.is_enabled
            except TenantFeatureFlag.DoesNotExist:
                pass
            except Exception as exc:  # noqa: BLE001
                log.warning("feature_flag.tenant_lookup_error: %s", exc)

        # 2. Global waffle
        waffle_state = _get_waffle_flag(flag_name, request)
        if waffle_state is not None:
            return waffle_state

        # 3. Settings default
        return _get_default(flag_name)

    @staticmethod
    def for_tenant(tenant: "Tenant", request=None) -> dict[str, bool]:
        """
        Return a dict of all known flag names and their resolved state for *tenant*.

        "Known" = union of:
        - All TenantFeatureFlag rows for this tenant
        - All keys in FEATURE_FLAGS_DEFAULTS
        """
        from django.conf import settings

        from apps.features.models import TenantFeatureFlag

        defaults: dict[str, bool] = getattr(settings, "FEATURE_FLAGS_DEFAULTS", {})

        # Start with defaults
        result: dict[str, bool] = dict(defaults)

        # Apply waffle for each default key
        for flag_name in list(result.keys()):
            waffle_state = _get_waffle_flag(flag_name, request)
            if waffle_state is not None:
                result[flag_name] = waffle_state

        # Apply per-tenant overrides (highest priority)
        overrides = TenantFeatureFlag.objects.filter(tenant=tenant)
        for override in overrides:
            result[override.flag_name] = override.is_enabled

        return result

    @staticmethod
    def set_for_tenant(
        tenant: "Tenant",
        flag_name: str,
        is_enabled: bool,
        source: str = "manual",
        note: str = "",
    ) -> None:
        """Create or update a per-tenant flag override."""
        from apps.features.models import TenantFeatureFlag

        TenantFeatureFlag.objects.update_or_create(
            tenant=tenant,
            flag_name=flag_name,
            defaults={"is_enabled": is_enabled, "source": source, "note": note},
        )

    @staticmethod
    def sync_plan_flags(tenant: "Tenant") -> None:
        """
        Auto-set plan-based flags when a tenant's subscription changes.

        Reads ``PLAN_FEATURE_FLAGS`` from settings::

            PLAN_FEATURE_FLAGS = {
                "free":    {"advanced_analytics": False, "api_access": False},
                "starter": {"advanced_analytics": False, "api_access": True},
                "pro":     {"advanced_analytics": True,  "api_access": True},
            }
        """
        from django.conf import settings

        plan_flags: dict[str, dict[str, bool]] = getattr(settings, "PLAN_FEATURE_FLAGS", {})
        if not plan_flags:
            return

        try:
            subscription = tenant.subscription
            plan_slug = subscription.plan.slug if subscription.plan else ""
        except Exception:  # noqa: BLE001
            return

        flags_for_plan = plan_flags.get(plan_slug, {})
        for flag_name, is_enabled in flags_for_plan.items():
            FeatureService.set_for_tenant(
                tenant=tenant,
                flag_name=flag_name,
                is_enabled=is_enabled,
                source="plan",
                note=f"Auto-set by plan: {plan_slug}",
            )
