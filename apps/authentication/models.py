"""Authentication models — TOTP two-factor authentication."""

from __future__ import annotations

import secrets
import uuid

from django.conf import settings
from django.db import models


def _generate_backup_codes() -> list[str]:
    """Return 8 single-use alphanumeric backup codes."""
    return [secrets.token_hex(5).upper() for _ in range(8)]


class UserTOTP(models.Model):
    """
    Stores TOTP 2FA state for a user.

    One row per user.  Created when the user initiates 2FA setup.
    ``is_enabled`` is set to True only after the user successfully verifies
    their first TOTP code (confirming the authenticator app is correctly
    configured).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="totp",
    )
    secret = models.CharField(
        max_length=64,
        help_text="Base32 TOTP secret (stored encrypted in production via field-level encryption).",
    )
    is_enabled = models.BooleanField(default=False)
    # Backup codes: list of plain-text codes.  Each is single-use.
    backup_codes = models.JSONField(default=_generate_backup_codes)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User TOTP"
        verbose_name_plural = "User TOTPs"

    def __str__(self) -> str:
        status = "enabled" if self.is_enabled else "pending"
        return f"TOTP({self.user}, {status})"

    def use_backup_code(self, code: str) -> bool:
        """Consume a backup code.  Returns True if the code was valid and unused."""
        code = code.strip().upper()
        if code in self.backup_codes:
            self.backup_codes = [c for c in self.backup_codes if c != code]
            self.save(update_fields=["backup_codes", "updated_at"])
            return True
        return False
