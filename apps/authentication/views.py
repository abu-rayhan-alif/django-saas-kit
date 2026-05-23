"""Authentication HTTP views — thin adapters over service layer."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from services.auth import PasswordResetService
from services.exceptions import ConflictServiceError, ValidationServiceError
from services.users import CreateUserInput, UserService

from apps.authentication.serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
)
from apps.users.serializers import UserSerializer

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

    @extend_schema(
        tags=["Auth"],
        request=RegisterSerializer,
        responses={
            201: UserSerializer,
            400: OpenApiResponse(description="Validation error"),
            409: OpenApiResponse(description="Username or email already taken"),
        },
        summary="Register a new user account",
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
        responses={
            200: OpenApiResponse(description="Password changed successfully."),
            400: OpenApiResponse(description="Invalid token, uid, or weak password."),
        },
        summary="Confirm password reset with token",
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

        return Response(
            {"detail": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )
