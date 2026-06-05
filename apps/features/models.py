"""Feature flags — per-tenant flag overrides on top of django-waffle.

Architecture
------------
``django-waffle`` (already installed) provides global flags, switches, and
samples.  This app layers *per-tenant* overrides so you can:

* Enable a beta feature for specific tenants (e.g. early-access customers).
* Hard-disable a flag for a tenant even when it's globally on.
* Tie a flag automatically to a plan slug.

Resolution order (highest to lowest priority):
1. ``TenantFeatureFlag`` row for the requesting tenant  →  on/off
2. Global waffle Flag / Switch for the flag name        →  on/off
3. ``FEATURE_FLAGS_DEFAULTS`` setting                   →  on/off
4. False (off by default)

Usage in views / services::

    from services.features import FeatureService

    if FeatureService.is_enabled("new_dashboard", request):
        ...
"""

from __future__ import annotations

from django.db import models


class TenantFeatureFlag(models.Model):
    """
    Per-tenant override for a named feature flag.

    A flag with ``is_enabled=True`` turns on the feature for this tenant
    regardless of the global waffle state.  ``is_enabled=False`` forces it off.
    """

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual (admin override)"
        PLAN = "plan", "Plan (auto-set by subscription plan)"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="feature_flags",
        db_index=True,
    )
    flag_name = models.CharField(
        max_length=100,
        help_text="Must match a waffle Flag name or a key in FEATURE_FLAGS_DEFAULTS.",
        db_index=True,
    )
    is_enabled = models.BooleanField(default=True)
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
    )
    note = models.TextField(
        blank=True,
        default="",
        help_text="Internal note about why this override exists.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("tenant", "flag_name")
        ordering = ["flag_name"]
        verbose_name = "Tenant Feature Flag"
        verbose_name_plural = "Tenant Feature Flags"

    def __str__(self) -> str:
        state = "ON" if self.is_enabled else "OFF"
        return f"{self.flag_name} → {state} ({self.tenant})"
