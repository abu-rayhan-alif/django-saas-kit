import uuid

from django.conf import settings
from django.db import models


class RoleChoices(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    MEMBER = "member", "Member"


# Numeric weight for hierarchy checks (higher = more privileged)
ROLE_HIERARCHY: dict[str, int] = {
    RoleChoices.OWNER: 3,
    RoleChoices.ADMIN: 2,
    RoleChoices.MEMBER: 1,
}


class UserTenantRole(models.Model):
    """
    Maps a user to a role within a specific tenant.

    Unique per (user, tenant) pair — a user can only hold one role per tenant.
    Roles do NOT transfer across tenants.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tenant_roles",
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="user_roles",
    )
    role = models.CharField(max_length=20, choices=RoleChoices.choices, db_index=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_assignments_made",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ("user", "tenant")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} — {self.role} in {self.tenant}"
