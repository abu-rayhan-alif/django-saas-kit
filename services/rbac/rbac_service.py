"""RBAC use-cases — no HTTP dependencies."""

from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser

from apps.rbac.models import RoleChoices, UserTenantRole
from apps.tenants.models import Tenant
from services.exceptions import ValidationServiceError


class RBACService:
    """Stateless service for role assignment and permission checks."""

    VALID_ROLES: frozenset[str] = frozenset(RoleChoices.values)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    @staticmethod
    def assign_role(
        user: AbstractBaseUser,
        tenant: Tenant,
        role: str,
        *,
        assigned_by: AbstractBaseUser | None = None,
    ) -> UserTenantRole:
        """
        Assign *role* to *user* in *tenant*.

        If the user already has a role in this tenant it is updated.
        Raises :exc:`~services.exceptions.ValidationServiceError` for an
        unrecognised role value.
        """
        if role not in RBACService.VALID_ROLES:
            raise ValidationServiceError(
                f"Invalid role '{role}'. Must be one of: "
                + ", ".join(sorted(RBACService.VALID_ROLES))
            )
        obj, _ = UserTenantRole.objects.update_or_create(
            user=user,
            tenant=tenant,
            defaults={"role": role, "assigned_by": assigned_by},
        )
        return obj

    @staticmethod
    def revoke_role(user: AbstractBaseUser, tenant: Tenant) -> bool:
        """
        Remove *user*'s role from *tenant*.

        Returns ``True`` if a role was deleted, ``False`` if none existed.
        """
        deleted, _ = UserTenantRole.objects.filter(user=user, tenant=tenant).delete()
        return bool(deleted)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    @staticmethod
    def get_role(user: AbstractBaseUser, tenant: Tenant) -> str | None:
        """Return the user's role string in *tenant*, or ``None``."""
        try:
            return UserTenantRole.objects.get(user=user, tenant=tenant).role
        except UserTenantRole.DoesNotExist:
            return None

    @staticmethod
    def has_role(
        user: AbstractBaseUser | None,
        tenant: Tenant,
        roles: list[str],
    ) -> bool:
        """
        Return ``True`` iff *user* is authenticated and holds one of *roles*
        in *tenant*.

        Role membership is strictly tenant-scoped — a role granted in tenant A
        has no effect in tenant B.
        """
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return UserTenantRole.objects.filter(
            user=user, tenant=tenant, role__in=roles
        ).exists()
