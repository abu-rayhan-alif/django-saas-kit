from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from services.rbac import RBACService

from apps.rbac.models import UserTenantRole
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

        user_role = RBACService.assign_role(user, tenant, role, assigned_by=request.user)
        return Response(
            UserTenantRoleSerializer(user_role).data,
            status=status.HTTP_201_CREATED,
        )


class RevokeRoleView(APIView):
    """
    POST /api/v1/rbac/<tenant_id>/roles/revoke/

    Revoke a user's role from the tenant entirely.
    Requires the caller to be an owner or admin of the tenant.

    Request body::

        { "user_id": 42 }
    """

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_roles = ["owner", "admin"]

    def post(self, request: Request, tenant_id):
        tenant = get_object_or_404(Tenant, id=tenant_id)
        serializer = RoleRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user_id"]
        revoked = RBACService.revoke_role(user, tenant)

        if not revoked:
            return Response(
                {"detail": "No role assignment found for this user in the tenant."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
