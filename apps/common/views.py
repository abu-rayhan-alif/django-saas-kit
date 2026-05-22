from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["System"],
        summary="Health check",
        description="Returns API availability status.",
        responses={200: OpenApiResponse(description="Service is healthy")},
    )
    def get(self, _request):
        return Response({"status": "ok"})
