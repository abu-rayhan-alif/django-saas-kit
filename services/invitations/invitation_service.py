"""InvitationService — tenant member invitation use-cases."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from services.exceptions import ConflictServiceError, NotFoundServiceError, ValidationServiceError

if TYPE_CHECKING:
    from apps.invitations.models import TenantInvitation

log = structlog.get_logger(__name__)


class InvitationService:
    """Manage the full lifecycle of tenant invitations."""

    @staticmethod
    def send_invitation(tenant, email: str, role: str, invited_by) -> TenantInvitation:
        """
        Create and send an invitation for *email* to join *tenant* as *role*.

        Raises:
            ConflictServiceError: Active invitation already exists for this email.
            ConflictServiceError: User is already a member of the tenant.
            ValidationServiceError: Role is invalid.
            PlanLimitExceededError: Plan member quota reached.
        """
        from apps.invitations.models import TenantInvitation  # noqa: PLC0415
        from apps.rbac.models import RoleChoices, UserTenantRole  # noqa: PLC0415
        from django.contrib.auth import get_user_model  # noqa: PLC0415

        from services.billing import PlanLimitService  # noqa: PLC0415

        email = email.strip().lower()

        if role not in RoleChoices.values:
            raise ValidationServiceError(
                f"Invalid role '{role}'. Must be one of: {', '.join(RoleChoices.values)}"
            )

        User = get_user_model()
        existing_user = User.objects.filter(email=email).first()
        if (
            existing_user
            and UserTenantRole.objects.filter(user=existing_user, tenant=tenant).exists()
        ):
            raise ConflictServiceError(f"{email} is already a member of this tenant.")

        if TenantInvitation.objects.filter(
            tenant=tenant, email=email, status=TenantInvitation.Status.PENDING
        ).exists():
            raise ConflictServiceError(
                f"A pending invitation already exists for {email}. Revoke it first."
            )

        PlanLimitService.check_member_limit(tenant)

        invitation = TenantInvitation.objects.create(
            tenant=tenant,
            email=email,
            role=role,
            invited_by=invited_by,
        )

        InvitationService._dispatch_email(invitation, invited_by)
        log.info("invitation.sent", tenant_id=str(tenant.pk), email=email, role=role)
        return invitation

    @staticmethod
    def accept_invitation(token: str, user) -> TenantInvitation:
        """
        Accept the invitation identified by *token* for *user*.

        Raises:
            NotFoundServiceError: Token not found or already used/revoked.
            ValidationServiceError: Invitation expired.
            ConflictServiceError: User already has a role in this tenant.
        """
        from apps.invitations.models import TenantInvitation  # noqa: PLC0415
        from apps.rbac.models import UserTenantRole  # noqa: PLC0415

        from services.rbac import RBACService  # noqa: PLC0415

        try:
            invitation = TenantInvitation.objects.select_related("tenant").get(token=token)
        except TenantInvitation.DoesNotExist as exc:
            raise NotFoundServiceError("Invitation not found.") from exc

        if invitation.status != TenantInvitation.Status.PENDING:
            raise NotFoundServiceError("This invitation has already been used or revoked.")

        if invitation.is_expired:
            invitation.status = TenantInvitation.Status.EXPIRED
            invitation.save(update_fields=["status"])
            raise ValidationServiceError("This invitation has expired.")

        if UserTenantRole.objects.filter(user=user, tenant=invitation.tenant).exists():
            raise ConflictServiceError("You are already a member of this tenant.")

        RBACService.assign_role(
            user, invitation.tenant, invitation.role, assigned_by=invitation.invited_by
        )

        invitation.status = TenantInvitation.Status.ACCEPTED
        invitation.accepted_by = user
        invitation.save(update_fields=["status", "accepted_by"])

        from apps.audit.models import AuditLog  # noqa: PLC0415

        from services.audit import AuditService  # noqa: PLC0415

        AuditService.log(
            AuditLog.Action.INVITATION_ACCEPTED,
            tenant=invitation.tenant,
            actor=user,
            resource_type="TenantInvitation",
            resource_id=str(invitation.pk),
            metadata={"email": invitation.email, "role": invitation.role},
        )
        log.info(
            "invitation.accepted",
            tenant_id=str(invitation.tenant_id),
            user_id=str(user.pk),
        )
        return invitation

    @staticmethod
    def revoke_invitation(invitation_id: str, tenant, revoked_by) -> TenantInvitation:
        """
        Revoke a pending invitation.

        Raises:
            NotFoundServiceError: Invitation not found in this tenant.
            ValidationServiceError: Invitation is not in PENDING state.
        """
        from apps.invitations.models import TenantInvitation  # noqa: PLC0415

        try:
            invitation = TenantInvitation.objects.get(pk=invitation_id, tenant=tenant)
        except TenantInvitation.DoesNotExist as exc:
            raise NotFoundServiceError("Invitation not found.") from exc

        if invitation.status != TenantInvitation.Status.PENDING:
            raise ValidationServiceError(
                f"Cannot revoke an invitation with status '{invitation.status}'."
            )

        invitation.status = TenantInvitation.Status.REVOKED
        invitation.save(update_fields=["status"])

        from apps.audit.models import AuditLog  # noqa: PLC0415

        from services.audit import AuditService  # noqa: PLC0415

        AuditService.log(
            AuditLog.Action.INVITATION_REVOKED,
            tenant=tenant,
            actor=revoked_by,
            resource_type="TenantInvitation",
            resource_id=str(invitation.pk),
            metadata={"email": invitation.email},
        )
        log.info("invitation.revoked", invitation_id=str(invitation.pk))
        return invitation

    @staticmethod
    def list_pending(tenant):
        """Return all pending (non-expired) invitations for *tenant*."""
        from apps.invitations.models import TenantInvitation  # noqa: PLC0415
        from django.utils import timezone  # noqa: PLC0415

        return TenantInvitation.objects.filter(
            tenant=tenant,
            status=TenantInvitation.Status.PENDING,
            expires_at__gt=timezone.now(),
        ).select_related("invited_by")

    @staticmethod
    def _dispatch_email(invitation, invited_by) -> None:
        """Fire-and-forget invitation email via Celery."""
        from apps.invitations.tasks import send_invitation_email  # noqa: PLC0415
        from django.conf import settings  # noqa: PLC0415

        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        accept_url = f"{frontend_url}/invitations/{invitation.token}/accept"

        invited_by_name = (
            f"{getattr(invited_by, 'first_name', '')} {getattr(invited_by, 'last_name', '')}".strip()
            or getattr(invited_by, "email", "Someone")
        )

        send_invitation_email.delay(
            recipient_email=invitation.email,
            tenant_name=invitation.tenant.name,
            invited_by_name=invited_by_name,
            role=invitation.role,
            accept_url=accept_url,
        )
