"""Feature flags API — exposes flag state for the current tenant."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from services.features import FeatureService


class FeatureFlagsView(APIView):
    """
    GET /api/v1/features/

    Return all known feature flags and their resolved state for the current
    tenant + user.  Clients can use this to conditionally render UI elements.

    Resolution order: per-tenant override → global waffle flag → settings default.

    Response::

        {
            "new_dashboard": true,
            "bulk_export": false,
            "api_access": true,
            ...
        }
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Features"],
        summary="List feature flags for current tenant",
        responses={
            200: OpenApiResponse(
                description="Map of flag_name → enabled (bool)",
                response={
                    "type": "object",
                    "additionalProperties": {"type": "boolean"},
                    "example": {
                        "new_dashboard": True,
                        "bulk_export": False,
                        "api_access": True,
                    },
                },
            )
        },
    )
    def get(self, request: Request) -> Response:
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            return Response({})
        flags = FeatureService.for_tenant(tenant, request=request)
        return Response(flags)


class FeatureFlagDetailView(APIView):
    """
    GET /api/v1/features/<flag_name>/

    Check a single feature flag for the current tenant.

    Response::

        {"flag_name": "new_dashboard", "enabled": true}
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Features"],
        summary="Check a single feature flag",
        responses={
            200: OpenApiResponse(
                description="Flag state",
                response={
                    "type": "object",
                    "properties": {
                        "flag_name": {"type": "string"},
                        "enabled": {"type": "boolean"},
                    },
                },
            )
        },
    )
    def get(self, request: Request, flag_name: str) -> Response:
        enabled = FeatureService.is_enabled(flag_name, request=request)
        return Response({"flag_name": flag_name, "enabled": enabled})
