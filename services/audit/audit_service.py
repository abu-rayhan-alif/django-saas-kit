"""AuditService — write-only audit log entries. Never reads from audit log."""

from __future__ import annotations

import structlog

log = structlog.get_logger(__name__)


def _get_client_ip(request) -> str | None:
    """Extract real IP, honouring X-Forwarded-For behind a reverse proxy."""
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


class AuditService:
    """Create immutable audit log entries for security-relevant events."""

    @staticmethod
    def log(
        action: str,
        *,
        request=None,
        tenant=None,
        actor=None,
        resource_type: str = "",
        resource_id: str = "",
        metadata: dict | None = None,
    ) -> None:
        """
        Write a single audit log entry.

        All parameters except *action* are optional.  Call from service layer
        or views — never from models.

        Args:
            action: One of ``AuditLog.Action`` choices.
            request: Current HTTP request (extracts IP, user-agent, actor).
            tenant: Tenant instance for the event scope.
            actor: User who performed the action (overrides request.user).
            resource_type: Model/domain name of the affected resource.
            resource_id: Primary key string of the affected resource.
            metadata: Extra key/value pairs persisted as JSON.
        """
        from apps.audit.models import AuditLog  # noqa: PLC0415

        try:
            resolved_actor = actor
            ip_address: str | None = None
            user_agent: str = ""
            actor_email: str = ""

            if request is not None:
                if (
                    resolved_actor is None
                    and hasattr(request, "user")
                    and request.user.is_authenticated
                ):
                    resolved_actor = request.user
                ip_address = _get_client_ip(request)
                user_agent = request.META.get("HTTP_USER_AGENT", "")

            if resolved_actor is not None:
                actor_email = getattr(resolved_actor, "email", "") or ""

            AuditLog.objects.create(
                tenant=tenant,
                actor=resolved_actor,
                actor_email=actor_email,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else "",
                metadata=metadata or {},
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception:  # noqa: BLE001 — audit must never break the happy path
            log.exception("audit.write_failed", action=action)
