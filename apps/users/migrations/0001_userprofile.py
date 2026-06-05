"""Initial migration — UserProfile model."""

from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import apps.users.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="profile",
                        serialize=False,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "avatar",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to=apps.users.models._avatar_upload_path,
                        help_text="Profile picture.",
                    ),
                ),
                (
                    "bio",
                    models.TextField(
                        blank=True,
                        default="",
                        max_length=500,
                        help_text="Short bio (max 500 characters).",
                    ),
                ),
                (
                    "phone",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=32,
                        help_text="Phone number in E.164 format.",
                    ),
                ),
                (
                    "timezone",
                    models.CharField(
                        blank=True,
                        default="UTC",
                        max_length=64,
                        help_text="IANA timezone name.",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "User Profile",
                "verbose_name_plural": "User Profiles",
            },
        ),
    ]
