from typing import cast

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from examples.demo_config import TENANT1_ID
from examples.openapi_examples import DEMO_RBAC_TENANT_ID
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from services.rbac import RBACService

from apps.rbac.models import RoleChoices, UserTenantRole
from apps.rbac.permissions import HasRolePermission
from apps.rbac.serializers import (
    RoleAssignSerializer,
    RoleRevokeSerializer,
    UserTenantRoleSerializer,
)
from apps.tenants.models import Tenant


class TenantRoleListView(APIView):
    """
    GET /api/v1/rbac/<tenant_id>/roles/

    List all role assignments for a tenant.
    Accessible by any authenticated member of the tenant.
    """

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_roles = ["owner", "admin", "member"]

    @extend_schema(
        tags=["RBAC"],
        summary="List role assignments for a tenant",
        description=(
            "Requires membership in the tenant. "
            f"After ``seed_demo``, Tenant One id is ``{TENANT1_ID}``."
        ),
        responses={200: UserTenantRoleSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                "tenant_id",
                OpenApiTypes.UUID,
                OpenApiParameter.PATH,
                description="Tenant workspace UUID",
                examples=[DEMO_RBAC_TENANT_ID],
            ),
        ],
    )
    def get(self, request: Request, tenant_id):
        tenant = get_object_or_404(Tenant, id=tenant_id)
        roles = UserTenantRole.objects.filter(tenant=tenant).select_related("user", "tenant")
        serializer = UserTenantRoleSerializer(roles, many=True)
        return Response(serializer.data)


class AssignRoleView(APIView):
    """
    POST /api/v1/rbac/<tenant_id>/roles/assign/

    Assign (or update) a role for a user within the tenant.
    Requires the caller to be an owner or admin of the tenant.

    Request body::

        { "user_id": 42, "role": "member" }
    """

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_roles = ["owner", "admin"]

    def post(self, request: Request, tenant_id):
        tenant = get_object_or_404(Tenant, id=tenant_id)
        serializer = RoleAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user_id"]  # validate_user_id returns the User
        role = serializer.validated_data["role"]

        user_role = RBACService.assign_role(
            user, tenant, role, assigned_by=cast(AbstractBaseUser, request.user)
        )
        return Response(
            UserTenantRoleSerializer(user_role).data,
            status=status.HTTP_201_CREATED,
        )


class RevokeRoleView(APIView):
    """Revoke a user's role within a tenant. Requires owner or admin."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_roles = [RoleChoices.OWNER, RoleChoices.ADMIN]

    @extend_schema(
        tags=["RBAC"],
        request=RoleRevokeSerializer,
        responses={204: None},
        summary="Revoke a role from a user within a tenant",
    )
    def post(self, request, tenant_id: str):
        tenant = get_object_or_404(Tenant, pk=tenant_id)
        serializer = RoleRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # validate_user_id already resolves the User object
        user = serializer.validated_data["user_id"]
        RBACService.revoke_role(user, tenant)
        return Response(status=status.HTTP_204_NO_CONTENT)
