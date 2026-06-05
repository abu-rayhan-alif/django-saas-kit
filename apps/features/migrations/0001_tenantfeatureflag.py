"""Initial migration — TenantFeatureFlag model."""

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TenantFeatureFlag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                (
                    "tenant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feature_flags",
                        to="tenants.tenant",
                    ),
                ),
                (
                    "flag_name",
                    models.CharField(
                        db_index=True,
                        help_text="Must match a waffle Flag name or FEATURE_FLAGS_DEFAULTS key.",
                        max_length=100,
                    ),
                ),
                ("is_enabled", models.BooleanField(default=True)),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("manual", "Manual (admin override)"),
                            ("plan", "Plan (auto-set by subscription plan)"),
                        ],
                        default="manual",
                        max_length=20,
                    ),
                ),
                ("note", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Tenant Feature Flag",
                "verbose_name_plural": "Tenant Feature Flags",
                "ordering": ["flag_name"],
                "unique_together": {("tenant", "flag_name")},
            },
        ),
    ]
