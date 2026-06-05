"""Initial migration — UserTOTP model for TOTP 2FA."""

from __future__ import annotations

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import apps.authentication.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserTOTP",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="totp",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "secret",
                    models.CharField(
                        help_text="Base32 TOTP secret.",
                        max_length=64,
                    ),
                ),
                ("is_enabled", models.BooleanField(default=False)),
                (
                    "backup_codes",
                    models.JSONField(default=apps.authentication.models._generate_backup_codes),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "User TOTP",
                "verbose_name_plural": "User TOTPs",
            },
        ),
    ]
