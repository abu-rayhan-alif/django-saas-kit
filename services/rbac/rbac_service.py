"""RBAC use-cases — no HTTP dependencies."""

from __future__ import annotations

from apps.rbac.models import RoleChoices, UserTenantRole
from apps.tenants.models import Tenant
from django.contrib.auth.models import AbstractBaseUser

from services.exceptions import ValidationServiceError


class RBACService:
    """Stateless service for role assignment and permission checks."""

    # TODO: Add your business logic here

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
            user_id=user.pk,
            tenant=tenant,
            defaults={"role": role, "assigned_by_id": assigned_by.pk if assigned_by else None},
        )
        return obj

    @staticmethod
    def revoke_role(user: AbstractBaseUser, tenant: Tenant) -> bool:
        """
        Remove *user*'s role from *tenant*.

        Returns ``True`` if a role was deleted, ``False`` if none existed.
        """
        deleted, _ = UserTenantRole.objects.filter(user_id=user.pk, tenant=tenant).delete()
        return bool(deleted)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    @staticmethod
    def get_role(user: AbstractBaseUser, tenant: Tenant) -> str | None:
        """Return the user's role string in *tenant*, or ``None``."""
        try:
            return UserTenantRole.objects.get(user_id=user.pk, tenant=tenant).role
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

        Django superusers are implicitly granted all roles across all tenants
        so that platform admins can manage any workspace without explicit
        role assignment.

        Role membership is otherwise strictly tenant-scoped — a role granted
        in tenant A has no effect in tenant B.
        """
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "is_superuser", False):
            return True
        return UserTenantRole.objects.filter(
            user_id=user.pk, tenant=tenant, role__in=roles
        ).exists()
