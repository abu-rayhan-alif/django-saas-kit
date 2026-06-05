"""User profile model — extended fields for the default Django User."""

from __future__ import annotations

import uuid
from zoneinfo import available_timezones

from django.conf import settings
from django.db import models

_VALID_TIMEZONES = available_timezones()


def _avatar_upload_path(instance: "UserProfile", filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"avatars/{instance.user_id}/{uuid.uuid4().hex}.{ext}"


class UserProfile(models.Model):
    """
    One-to-one extension of the Django User model with optional profile fields.

    All fields are optional so existing users are not broken by this migration.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        primary_key=True,
    )
    avatar = models.ImageField(
        upload_to=_avatar_upload_path,
        null=True,
        blank=True,
        help_text="Profile picture.",
    )
    bio = models.TextField(
        blank=True,
        default="",
        max_length=500,
        help_text="Short bio (max 500 characters).",
    )
    phone = models.CharField(
        blank=True,
        default="",
        max_length=32,
        help_text="Phone number in E.164 format, e.g. +8801700000000.",
    )
    timezone = models.CharField(
        blank=True,
        default="UTC",
        max_length=64,
        help_text="IANA timezone name, e.g. Asia/Dhaka.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self) -> str:
        return f"Profile({self.user})"

    def clean(self) -> None:
        from django.core.exceptions import ValidationError
        if self.timezone and self.timezone not in _VALID_TIMEZONES:
            raise ValidationError({"timezone": f"Unknown timezone: {self.timezone!r}"})

    @property
    def avatar_url(self) -> str | None:
        if self.avatar:
            try:
                return self.avatar.url
            except Exception:
                return None
        return None
