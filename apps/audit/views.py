"""Audit log REST views — read-only, tenant-scoped, admin/owner only."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.rbac.permissions import HasRolePermission


class AuditLogListView(ListAPIView):
    """
    GET /api/v1/audit-logs/

    Paginated audit log for the current tenant.  Owner/admin only.

    Query parameters
    ----------------
    action    — filter by action code (e.g. ``login``, ``role_assigned``)
    actor     — filter by actor email (partial, case-insensitive)
    """

    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_roles = ["owner", "admin"]
    ordering = ["-timestamp"]

    @extend_schema(
        tags=["Audit"],
        summary="List audit log entries for the current tenant",
        parameters=[
            OpenApiParameter("action", description="Filter by action code", required=False),
            OpenApiParameter(
                "actor", description="Filter by actor email (partial match)", required=False
            ),
        ],
        responses={200: AuditLogSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        if tenant is None:
            return AuditLog.objects.none()

        qs = AuditLog.objects.filter(tenant=tenant)

        action = self.request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)

        actor = self.request.query_params.get("actor")
        if actor:
            qs = qs.filter(actor_email__icontains=actor)

        return qs
