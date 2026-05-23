from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.health_checks import run_readiness_checks


class HealthCheckView(APIView):
    """
    Liveness probe — process is running (SAAS-602).

    Does not check external dependencies; use ``GET /ready/`` for that.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes: list = []

    @extend_schema(
        tags=["System"],
        summary="Liveness check",
        description="Returns 200 when the Django process can serve HTTP (no dependency checks).",
        responses={200: OpenApiResponse(description="Application is alive")},
    )
    def get(self, _request):
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class ReadinessCheckView(APIView):
    """
    Readiness probe — database and Redis reachable (SAAS-602).

    Returns 503 when any dependency check fails.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes: list = []

    @extend_schema(
        tags=["System"],
        summary="Readiness check",
        description="Verifies database and Redis connectivity. Returns 503 if any check fails.",
        responses={
            200: OpenApiResponse(description="All dependency checks passed"),
            503: OpenApiResponse(description="One or more dependency checks failed"),
        },
    )
    def get(self, _request):
        checks, all_ok = run_readiness_checks()
        body = {
            "status": "ok" if all_ok else "not_ready",
            "checks": checks,
        }
        http_status = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(body, status=http_status)
