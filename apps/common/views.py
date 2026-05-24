from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.health_checks import run_readiness_checks


class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes: list = []

    @extend_schema(
        tags=["System"],
        summary="Health check",
        description="Returns API availability status.",
        responses={200: OpenApiResponse(description="Service is healthy")},
    )
    def get(self, _request):
        return Response({"status": "ok"})


class ReadinessCheckView(APIView):
    """
    GET /ready/

    Deep health check -- verifies database and Redis connectivity.
    Returns HTTP 200 when all probes pass, HTTP 503 otherwise.
    Used by orchestrators (Kubernetes, Docker Compose) to gate traffic.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes: list = []

    @extend_schema(
        tags=["System"],
        summary="Readiness check",
        description=(
            "Deep health probe: verifies database and Redis connectivity. "
            "Returns 200 when all dependencies are reachable, 503 otherwise."
        ),
        responses={
            200: OpenApiResponse(description="All dependencies healthy"),
            503: OpenApiResponse(description="One or more dependencies unavailable"),
        },
    )
    def get(self, _request):
        checks, all_ok = run_readiness_checks()
        http_status = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(
            {"status": "ok" if all_ok else "not_ready", "checks": checks},
            status=http_status,
        )
