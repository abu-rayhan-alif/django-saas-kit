"""Invitation REST views."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from services.exceptions import (
    ConflictServiceError,
    NotFoundServiceError,
    PlanLimitExceededError,
    ValidationServiceError,
)
from services.invitations import InvitationService

from apps.invitations.serializers import (
    InvitationAcceptSerializer,
    InvitationCreateSerializer,
    InvitationSerializer,
)
from apps.rbac.permissions import HasRolePermission


class TenantInvitationListCreateView(APIView):
    """
    GET  /api/v1/invitations/          — list pending invitations for current tenant
    POST /api/v1/invitations/          — send a new invitation
    """

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_roles = ["owner", "admin"]

    @extend_schema(
        tags=["Invitations"],
        summary="List pending invitations for the current tenant",
        responses={200: InvitationSerializer(many=True)},
    )
    def get(self, request):
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            return Response(
                {"detail": "Tenant context required."}, status=status.HTTP_400_BAD_REQUEST
            )
        invitations = InvitationService.list_pending(tenant)
        return Response(InvitationSerializer(invitations, many=True).data)

    @extend_schema(
        tags=["Invitations"],
        summary="Invite a new member to the current tenant",
        request=InvitationCreateSerializer,
        responses={201: InvitationSerializer, 409: None, 402: None},
    )
    def post(self, request):
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            return Response(
                {"detail": "Tenant context required."}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            invitation = InvitationService.send_invitation(
                tenant=tenant,
                email=serializer.validated_data["email"],
                role=serializer.validated_data["role"],
                invited_by=request.user,
            )
        except ConflictServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except PlanLimitExceededError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_402_PAYMENT_REQUIRED)
        except ValidationServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(InvitationSerializer(invitation).data, status=status.HTTP_201_CREATED)


class InvitationDetailView(APIView):
    """
    GET /api/v1/invitations/{token}/

    Public endpoint — returns invitation metadata so the frontend can display
    the invitation page before the user logs in / registers.
    """

    permission_classes = []
    authentication_classes = []

    @extend_schema(
        tags=["Invitations"],
        summary="Get invitation details by token (public)",
        responses={200: InvitationSerializer, 404: None},
    )
    def get(self, request, token: str):
        from apps.invitations.models import TenantInvitation  # noqa: PLC0415

        try:
            invitation = TenantInvitation.objects.select_related("tenant", "invited_by").get(
                token=token, status=TenantInvitation.Status.PENDING
            )
        except TenantInvitation.DoesNotExist:
            return Response({"detail": "Invitation not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(InvitationSerializer(invitation).data)


class InvitationAcceptView(APIView):
    """
    POST /api/v1/invitations/{token}/accept/

    Accept an invitation. The authenticated user is joined to the tenant.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Invitations"],
        summary="Accept an invitation",
        request=InvitationAcceptSerializer,
        responses={200: InvitationSerializer, 400: None, 404: None, 409: None},
    )
    def post(self, request, token: str):
        try:
            invitation = InvitationService.accept_invitation(token=token, user=request.user)
        except NotFoundServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ValidationServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ConflictServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(InvitationSerializer(invitation).data)


class InvitationRevokeView(APIView):
    """
    DELETE /api/v1/invitations/{id}/

    Revoke a pending invitation. Owner/admin only.
    """

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_roles = ["owner", "admin"]

    @extend_schema(
        tags=["Invitations"],
        summary="Revoke a pending invitation",
        responses={204: None, 400: None, 404: None},
    )
    def delete(self, request, invitation_id: str):
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            return Response(
                {"detail": "Tenant context required."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            InvitationService.revoke_invitation(
                invitation_id=invitation_id,
                tenant=tenant,
                revoked_by=request.user,
            )
        except NotFoundServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ValidationServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)
