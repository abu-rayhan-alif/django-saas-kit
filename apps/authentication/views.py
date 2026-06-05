"""Authentication HTTP views — thin adapters over service layer."""

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from examples.demo_config import DEMO_ADMIN
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from services.audit import AuditService
from services.auth import PasswordResetService
from services.exceptions import ConflictServiceError, ValidationServiceError
from services.users import CreateUserInput, UserService

from apps.audit.models import AuditLog
from apps.authentication.serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
)
from apps.common.throttling import PasswordResetRateThrottle, RegisterRateThrottle
from apps.users.serializers import UserSerializer


def _demo_examples(*examples: OpenApiExample) -> list[OpenApiExample]:
    """Return demo examples for API documentation. Always included; these are non-sensitive demo credentials."""
    return list(examples)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class RegisterView(APIView):
    """
    POST /api/v1/auth/register/

    Create a new user account.  Returns the created user on success.
    Delegates entirely to ``UserService.create_user`` — no auth required.
    """

    permission_classes = [AllowAny]
    throttle_classes = [RegisterRateThrottle]
    throttle_scope = "register"

    @extend_schema(
        tags=["Auth"],
        request=RegisterSerializer,
        responses={
            201: UserSerializer,
            400: OpenApiResponse(description="Validation error"),
            409: OpenApiResponse(description="Username or email already taken"),
        },
        summary="Register a new user account",
        examples=_demo_examples(
            OpenApiExample(
                "Register (non-demo)",
                value={
                    "email": "newuser@example.com",
                    "username": "newuser",
                    "password": "SecurePass123!",
                    "first_name": "New",
                    "last_name": "User",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Demo admin already exists",
                description="Use login instead — created by ``seed_demo``.",
                value={
                    "email": DEMO_ADMIN.email,
                    "username": DEMO_ADMIN.username,
                    "password": DEMO_ADMIN.password,
                },
                request_only=True,
            ),
        ),
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = UserService.create_user(CreateUserInput(**serializer.validated_data))
        except ValidationServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ConflictServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        AuditService.log(
            AuditLog.Action.USER_REGISTERED,
            request=request,
            resource_type="User",
            resource_id=str(user.pk),
            metadata={"username": user.username},
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Password reset — request
# ---------------------------------------------------------------------------


_RESET_REQUEST_200 = OpenApiResponse(
    description="Reset email sent (returned even if email is not registered)."
)


class PasswordResetRequestView(APIView):
    """
    POST /api/v1/auth/password/reset/

    Trigger a password-reset email.  Always returns HTTP 200 regardless of
    whether the email address exists, to prevent user-enumeration attacks.
    """

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]
    throttle_scope = "password_reset"

    @extend_schema(
        tags=["Auth"],
        request=PasswordResetRequestSerializer,
        responses={200: _RESET_REQUEST_200},
        summary="Request a password-reset email",
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        PasswordResetService.request_reset(email=serializer.validated_data["email"])

        AuditService.log(
            AuditLog.Action.PASSWORD_RESET_REQUESTED,
            request=request,
            metadata={"email": serializer.validated_data["email"]},
        )
        return Response(
            {"detail": "If that email is registered, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Password reset — confirm
# ---------------------------------------------------------------------------


class PasswordResetConfirmView(APIView):
    """
    POST /api/v1/auth/password/reset/confirm/

    Validate a reset token (uid + token from the email) and set a new password.
    The token is single-use — it becomes invalid once the password is changed.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        request=PasswordResetConfirmSerializer,
        responses={200: OpenApiResponse(description="Password reset successful")},
        summary="Confirm password reset",
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            PasswordResetService.confirm_reset(
                uid=serializer.validated_data["uid"],
                token=serializer.validated_data["token"],
                new_password=serializer.validated_data["new_password"],
            )
        except ValidationServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Password reset successful."}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Throttled token view (with demo example for Swagger)
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["Auth"],
    summary="Obtain JWT access + refresh token pair",
    examples=_demo_examples(
        OpenApiExample(
            "Demo admin login",
            description="Created by seed_demo. Use this to explore the API.",
            value={
                "username": DEMO_ADMIN.username,
                "password": DEMO_ADMIN.password,
            },
            request_only=True,
        ),
    ),
)
class ThrottledTokenObtainPairView(TokenObtainPairView):
    """
    Token endpoint with login-scoped rate limiting (5/minute by default).

    If the authenticating user has 2FA enabled, this view does NOT return a
    JWT pair.  Instead it returns::

        {"two_fa_required": true, "session_key": "<key>"}

    The client must then POST ``{"session_key": "<key>", "code": "<totp>"}``
    to ``/api/v1/auth/2fa/complete/`` to receive the actual JWT pair.
    The session_key expires after 5 minutes.
    """

    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        import secrets as _secrets

        from django.core.cache import cache

        response = super().post(request, *args, **kwargs)

        # super() raises on bad credentials, so reaching here means auth succeeded.
        # Identify the user from the validated serializer.
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=False)
            user = serializer.user  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            return response

        if user is None:
            return response

        totp_obj = getattr(user, "totp", None)
        if totp_obj and totp_obj.is_enabled:
            session_key = _secrets.token_urlsafe(32)
            cache.set(f"2fa_pre_auth:{session_key}", user.pk, timeout=300)
            return Response(
                {"two_fa_required": True, "session_key": session_key},
                status=status.HTTP_200_OK,
            )

        return response
