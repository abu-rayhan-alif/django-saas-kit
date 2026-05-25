"""Billing models — Plan definitions, Subscription state per Tenant."""

from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class Plan(models.Model):
    """
    A subscription plan that defines feature limits for a tenant.

    Plans are created/managed in the Django admin and matched to Stripe
    price IDs.  When billing is disabled, assign the ``free`` plan.
    """

    slug = models.SlugField(unique=True, max_length=50)
    name = models.CharField(max_length=100)
    stripe_price_id = models.CharField(max_length=255, blank=True, default="")
    max_members = models.PositiveIntegerField(
        default=5,
        help_text="Maximum number of members per tenant. 0 = unlimited.",
    )
    max_storage_mb = models.PositiveIntegerField(
        default=1024,
        help_text="Storage quota in MiB. 0 = unlimited.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def is_unlimited_members(self) -> bool:
        return self.max_members == 0

    def is_unlimited_storage(self) -> bool:
        return self.max_storage_mb == 0


class Subscription(models.Model):
    class Status(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        UNPAID = "unpaid", "Unpaid"
        CANCELED = "canceled", "Canceled"
        PAUSED = "paused", "Paused"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
    )
    stripe_customer_id = models.CharField(max_length=255, unique=True, db_index=True)
    stripe_subscription_id = models.CharField(
        max_length=255, unique=True, null=True, blank=True, db_index=True
    )
    stripe_price_id = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TRIALING, db_index=True
    )
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    # Grace window during dunning — access allowed until this timestamp even if past_due
    grace_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    trial_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.tenant} — {self.status}"

    def is_access_allowed(self) -> bool:
        """Return True if the tenant should be granted product access."""
        if self.status in (self.Status.ACTIVE, self.Status.TRIALING):
            return True
        if self.status == self.Status.PAST_DUE and self.grace_period_end:
            return timezone.now() < self.grace_period_end
        return False


class WebhookEvent(models.Model):
    """Idempotency log for Stripe webhook events."""

    stripe_event_id = models.CharField(max_length=255, unique=True, primary_key=True)
    event_type = models.CharField(max_length=100, db_index=True)
    processed_at = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField(default=dict)

    class Meta:
        ordering = ["-processed_at"]

    def __str__(self) -> str:
        return f"{self.event_type} — {self.stripe_event_id}"
