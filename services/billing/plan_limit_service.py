"""Plan limit enforcement — checks tenant quotas before mutations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from services.exceptions import PlanLimitExceededError

if TYPE_CHECKING:
    from apps.billing.models import Plan
    from apps.tenants.models import Tenant

log = structlog.get_logger(__name__)


class PlanLimitService:
    """
    Stateless service for enforcing subscription plan limits.

    Call ``check_member_limit(tenant)`` before adding a new member to a
    tenant.  Raises ``PlanLimitExceededError`` if the quota is reached.

    Usage::

        PlanLimitService.check_member_limit(tenant)  # raises if over limit
    """

    @staticmethod
    def get_plan(tenant: Tenant) -> Plan | None:
        """Return the Plan associated with *tenant*'s subscription, or None."""
        try:
            sub = tenant.subscription
            return sub.plan
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def get_member_count(tenant: Tenant) -> int:
        """Count current members (any role) in *tenant*."""
        from apps.rbac.models import UserTenantRole  # noqa: PLC0415

        return UserTenantRole.objects.filter(tenant=tenant).count()

    @staticmethod
    def check_member_limit(tenant: Tenant) -> None:
        """
        Raise ``PlanLimitExceededError`` if adding another member would
        exceed the tenant's plan quota.

        If the tenant has no plan, limits are not enforced (default free tier
        falls back to plan defaults defined on the ``Plan`` model).
        """
        plan = PlanLimitService.get_plan(tenant)
        if plan is None or plan.is_unlimited_members():
            return

        current = PlanLimitService.get_member_count(tenant)
        if current >= plan.max_members:
            log.warning(
                "plan_limit.members_exceeded",
                tenant_id=str(tenant.pk),
                current=current,
                max_members=plan.max_members,
                plan=plan.slug,
            )
            raise PlanLimitExceededError(
                f"Your plan allows up to {plan.max_members} member(s). "
                f"Upgrade your plan to add more members."
            )
