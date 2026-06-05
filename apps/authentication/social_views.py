"""Social OAuth views — exchange a provider access token for a JWT pair."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from services.auth.social_auth_service import SocialAuthService
from services.exceptions import ConflictServiceError, ValidationServiceError


class SocialAuthView(APIView):
    """
    POST /api/v1/auth/social/

    Exchange a provider OAuth access token for a Django SaaS Kit JWT pair.

    Supported providers: ``google``, ``github``

    The client handles the OAuth flow (redirect → callback → access_token)
    and then calls this endpoint with the resulting access token.  This view
    validates the token against the provider's API, creates the user on first
    login, and returns a standard JWT pair.

    **Google flow**:
    1. Redirect user to Google OAuth consent screen.
    2. Exchange the authorisation code for an access token.
    3. POST ``{"provider": "google", "access_token": "<token>"}`` here.

    **GitHub flow**:
    1. Redirect user to GitHub OAuth consent screen.
    2. Exchange the authorisation code for an access token.
    3. POST ``{"provider": "github", "access_token": "<token>"}`` here.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Social OAuth login (Google / GitHub)",
        request={
            "application/json": {
                "type": "object",
                "required": ["provider", "access_token"],
                "properties": {
                    "provider": {
                        "type": "string",
                        "enum": ["google", "github"],
                        "description": "OAuth provider name.",
                    },
                    "access_token": {
                        "type": "string",
                        "description": "Access token obtained from the OAuth provider.",
                    },
                },
            }
        },
        responses={
            200: OpenApiResponse(
                description="JWT pair issued",
                response={
                    "type": "object",
                    "properties": {
                        "access": {"type": "string"},
                        "refresh": {"type": "string"},
                        "created": {
                            "type": "boolean",
                            "description": "True if a new account was just created.",
                        },
                    },
                },
            ),
            400: OpenApiResponse(description="Missing / invalid fields"),
            401: OpenApiResponse(description="Provider token validation failed"),
            409: OpenApiResponse(description="Email already registered via another method"),
        },
        examples=[
            OpenApiExample(
                "Google login",
                value={"provider": "google", "access_token": "ya29.a0AfH..."},
                request_only=True,
            ),
            OpenApiExample(
                "GitHub login",
                value={"provider": "github", "access_token": "gho_16C7e4..."},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        provider = request.data.get("provider", "").strip()
        access_token = request.data.get("access_token", "").strip()

        if not provider:
            return Response(
                {"detail": "provider is required.", "field": "provider"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not access_token:
            return Response(
                {"detail": "access_token is required.", "field": "access_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = SocialAuthService.authenticate(provider, access_token)
        except ValidationServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
        except ConflictServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        created = not getattr(user, "_pre_existing", True)
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "created": created,
            },
            status=status.HTTP_200_OK,
        )
