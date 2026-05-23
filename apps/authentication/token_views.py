"""JWT token views with OpenAPI demo examples."""

from drf_spectacular.utils import extend_schema
from examples.openapi_examples import DEMO_LOGIN_REQUEST
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView


@extend_schema(
    tags=["Auth"],
    summary="Obtain JWT access and refresh tokens",
    description=(
        "Exchange username and password for access and refresh tokens. "
        "Use **Authorize** in Swagger with `Bearer <access>`."
    ),
    examples=[DEMO_LOGIN_REQUEST],
)
class TokenObtainPairView(BaseTokenObtainPairView):
    pass


@extend_schema(
    tags=["Auth"],
    summary="Refresh JWT access token",
)
class TokenRefreshView(BaseTokenRefreshView):
    pass
