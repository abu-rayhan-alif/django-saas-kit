"""Tenant invitation model."""

from __future__ import annotations

import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.rbac.models import RoleChoices

_TOKEN_BYTES = 32
_EXPIRY_HOURS = 72


def _default_token() -> str:
    return secrets.token_urlsafe(_TOKEN_BYTES)


def _default_expires_at():
    from datetime import timedelta
    return timezone.now() + timedelta(hours=_EXPIRY_HOURS)


class TenantInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField()
    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.MEMBER,
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        default=_default_token,
        editable=False,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_invitations",
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_invitations",
    )
    expires_at = models.DateTimeField(default=_default_expires_at)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"], name="inv_tenant_status_idx"),
            models.Index(fields=["email", "tenant"], name="inv_email_tenant_idx"),
        ]

    def __str__(self) -> str:
        return f"Invite {self.email} → {self.tenant} ({self.status})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_usable(self) -> bool:
        return self.status == self.Status.PENDING and not self.is_expired
