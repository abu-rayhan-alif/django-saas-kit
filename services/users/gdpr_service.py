"""GDPR Article 17 — Right to be Forgotten (NEW-06).

Policy
------
anonymize (default)
    Wipes all PII fields on the User row but keeps the row so that
    SET_NULL audit FKs (created_by, updated_by, deleted_by on BaseModel)
    continue to point at a non-personally-identifiable placeholder row.
    Personal child records (Notification, UserTenantRole) are hard-deleted.
    All outstanding JWT tokens are revoked.

hard_delete
    Removes the User row entirely.  Child records are explicitly deleted first
    so accurate counts can be reported; then user.delete() handles any remaining
    CASCADE / SET_NULL relations declared on the models.

FK handling
-----------
Model                        FK to User          on_delete    Action
-----                        ----------          ---------    ------
Notification.user            direct (personal)   CASCADE      explicit hard-delete
UserTenantRole.user          direct (membership) CASCADE      explicit hard-delete
UserTenantRole.assigned_by   audit               SET_NULL     left to Django (no PII)
BaseModel.created_by/        audit               SET_NULL     left to Django (no PII)
  updated_by / deleted_by
OutstandingToken.user        JWT session         SET_NULL     explicit delete
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import structlog

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ErasureResult:
    user_id: Any
    mode: str  # "anonymize" | "hard_delete"
    notifications_deleted: int
    roles_deleted: int
    tokens_deleted: int


class GDPRService:
    """Stateless service implementing GDPR right-to-erasure for one user."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def anonymize(user: Any) -> ErasureResult:
        """
        Wipe all PII from the user row and hard-delete personal child records.

        The user row is kept with a randomised placeholder identity so that
        SET_NULL audit FKs in other tables remain valid (a null FK is fine,
        but keeping the row avoids surprises in admin queries).
        """
        from django.db import transaction  # noqa: PLC0415

        with transaction.atomic():
            n_tokens = GDPRService._revoke_tokens(user)
            n_notifs = GDPRService._delete_notifications(user)
            n_roles = GDPRService._delete_roles(user)

            tag = uuid.uuid4().hex[:12]
            user.username = f"deleted_{tag}"
            user.email = f"deleted_{tag}@deleted.invalid"
            user.first_name = ""
            user.last_name = ""
            user.is_active = False
            user.set_unusable_password()
            user.save(
                update_fields=[
                    "username",
                    "email",
                    "first_name",
                    "last_name",
                    "is_active",
                    "password",
                ]
            )

        log.info(
            "gdpr.anonymize",
            user_id=user.pk,
            notifications_deleted=n_notifs,
            roles_deleted=n_roles,
            tokens_deleted=n_tokens,
        )
        return ErasureResult(
            user_id=user.pk,
            mode="anonymize",
            notifications_deleted=n_notifs,
            roles_deleted=n_roles,
            tokens_deleted=n_tokens,
        )

    @staticmethod
    def hard_delete(user: Any) -> ErasureResult:
        """
        Permanently remove the user row and all directly owned child records.

        Child rows are deleted explicitly (for accurate counts) before
        user.delete() runs.  Any remaining CASCADE / SET_NULL relations
        declared on models are handled by Django automatically.
        """
        from django.db import transaction  # noqa: PLC0415

        user_pk = user.pk
        with transaction.atomic():
            n_tokens = GDPRService._revoke_tokens(user)
            n_notifs = GDPRService._delete_notifications(user)
            n_roles = GDPRService._delete_roles(user)
            user.delete()

        log.info(
            "gdpr.hard_delete",
            user_id=user_pk,
            notifications_deleted=n_notifs,
            roles_deleted=n_roles,
            tokens_deleted=n_tokens,
        )
        return ErasureResult(
            user_id=user_pk,
            mode="hard_delete",
            notifications_deleted=n_notifs,
            roles_deleted=n_roles,
            tokens_deleted=n_tokens,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _revoke_tokens(user: Any) -> int:
        """Delete all outstanding JWT tokens (simplejwt uses SET_NULL, not CASCADE)."""
        try:
            from rest_framework_simplejwt.token_blacklist.models import (  # noqa: PLC0415
                OutstandingToken,
            )
        except ImportError:
            return 0

        qs = OutstandingToken.objects.filter(user=user)
        count, _ = qs.delete()
        return count

    @staticmethod
    def _delete_notifications(user: Any) -> int:
        from apps.notifications.models import Notification  # noqa: PLC0415

        count, _ = Notification.objects.filter(user=user).delete()
        return count

    @staticmethod
    def _delete_roles(user: Any) -> int:
        from apps.rbac.models import UserTenantRole  # noqa: PLC0415

        count, _ = UserTenantRole.objects.filter(user=user).delete()
        return count
