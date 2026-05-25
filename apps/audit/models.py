"""Audit log — immutable record of security-relevant actions within a tenant."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        # Authentication
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"
        LOGIN_FAILED = "login_failed", "Login Failed"
        PASSWORD_RESET_REQUESTED = "password_reset_requested", "Password Reset Requested"
        PASSWORD_RESET_CONFIRMED = "password_reset_confirmed", "Password Reset Confirmed"
        # User lifecycle
        USER_REGISTERED = "user_registered", "User Registered"
        USER_DELETED = "user_deleted", "User Deleted (GDPR)"
        # RBAC
        ROLE_ASSIGNED = "role_assigned", "Role Assigned"
        ROLE_REVOKED = "role_revoked", "Role Revoked"
        # Invitations
        MEMBER_INVITED = "member_invited", "Member Invited"
        INVITATION_ACCEPTED = "invitation_accepted", "Invitation Accepted"
        INVITATION_REVOKED = "invitation_revoked", "Invitation Revoked"
        # Billing
        SUBSCRIPTION_CREATED = "subscription_created", "Subscription Created"
        SUBSCRIPTION_UPDATED = "subscription_updated", "Subscription Updated"
        SUBSCRIPTION_CANCELED = "subscription_canceled", "Subscription Canceled"
        PAYMENT_SUCCEEDED = "payment_succeeded", "Payment Succeeded"
        PAYMENT_FAILED = "payment_failed", "Payment Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_logs",
        db_index=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    actor_email = models.EmailField(blank=True)
    action = models.CharField(max_length=50, choices=Action.choices, db_index=True)
    resource_type = models.CharField(max_length=100, blank=True)
    resource_id = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["tenant", "timestamp"], name="audit_tenant_ts_idx"),
            models.Index(fields=["tenant", "action"], name="audit_tenant_action_idx"),
            models.Index(fields=["actor", "timestamp"], name="audit_actor_ts_idx"),
        ]

    def __str__(self) -> str:
        actor = self.actor_email or "system"
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {actor} — {self.action}"
