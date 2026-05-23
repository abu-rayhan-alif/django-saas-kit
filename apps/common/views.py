from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.health_checks import check_database, check_redis


class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["System"],
        summary="Health check",
        description="Returns API availability and dependency checks (database, Redis).",
        responses={
            200: OpenApiResponse(description="All checks passed"),
            503: OpenApiResponse(description="One or more dependency checks failed"),
        },
    )
    def get(self, _request):
        checks: dict[str, str] = {}

        try:
            checks["database"] = check_database()
        except Exception:
            checks["database"] = "error"

        try:
            checks["redis"] = check_redis()
        except Exception:
            checks["redis"] = "error"

        all_ok = all(value == "ok" for value in checks.values())
        body = {
            "status": "ok" if all_ok else "degraded",
            "checks": checks,
        }
        http_status = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(body, status=http_status)
