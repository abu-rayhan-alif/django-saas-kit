"""Two-Factor Authentication (TOTP) views."""

from __future__ import annotations

import io

import pyotp
import qrcode
import qrcode.image.svg
from django.core.cache import cache
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import UserTOTP

_CACHE_TTL = 300  # 5 minutes for pre-auth sessions
_CACHE_PREFIX = "2fa_pre_auth:"


def _get_provisioning_uri(user, secret: str) -> str:
    """Return an otpauth:// URI for QR code generation."""
    from django.conf import settings

    issuer = getattr(settings, "SITE_NAME", "Django SaaS Kit")
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=user.email, issuer_name=issuer)


def _make_qr_svg(uri: str) -> str:
    """Return the provisioning URI QR code as an inline SVG string."""
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(uri, image_factory=factory, box_size=10)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode("utf-8")


class TwoFactorSetupView(APIView):
    """
    GET /api/v1/auth/2fa/setup/

    Begin 2FA setup.  Returns a new TOTP secret, provisioning URI, and an
    inline SVG QR code to scan with an authenticator app (Google Authenticator,
    Authy, etc.).

    Calling this endpoint again generates a fresh secret and invalidates the
    previous one (if 2FA was not yet enabled).  If 2FA is already enabled,
    returns ``{"detail": "2FA is already enabled."}`` with HTTP 400.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth / 2FA"],
        summary="Begin TOTP 2FA setup",
        responses={
            200: OpenApiResponse(
                description="Secret and QR code returned",
                response={
                    "type": "object",
                    "properties": {
                        "secret": {"type": "string"},
                        "provisioning_uri": {"type": "string"},
                        "qr_svg": {"type": "string", "description": "Inline SVG QR code"},
                    },
                },
            ),
            400: OpenApiResponse(description="2FA already enabled"),
        },
    )
    def get(self, request):
        user = request.user
        totp_obj = getattr(user, "totp", None)
        if totp_obj and totp_obj.is_enabled:
            return Response(
                {"detail": "2FA is already enabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        secret = pyotp.random_base32()

        # Upsert: create or refresh the pending TOTP record
        UserTOTP.objects.update_or_create(
            user=user,
            defaults={"secret": secret, "is_enabled": False},
        )

        uri = _get_provisioning_uri(user, secret)
        svg = _make_qr_svg(uri)

        return Response(
            {
                "secret": secret,
                "provisioning_uri": uri,
                "qr_svg": svg,
            }
        )


class TwoFactorVerifyEnableView(APIView):
    """
    POST /api/v1/auth/2fa/enable/

    Verify the first TOTP code from the authenticator app and activate 2FA.
    Returns backup codes — show them to the user once and store them securely.

    Body: ``{"code": "123456"}``
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth / 2FA"],
        summary="Enable 2FA after verifying first TOTP code",
        request={
            "application/json": {
                "type": "object",
                "required": ["code"],
                "properties": {"code": {"type": "string", "example": "123456"}},
            }
        },
        responses={
            200: OpenApiResponse(description="2FA enabled, backup codes returned"),
            400: OpenApiResponse(description="Invalid code or 2FA not set up"),
        },
    )
    def post(self, request):
        code = request.data.get("code", "").strip()
        if not code:
            return Response({"detail": "code is required."}, status=status.HTTP_400_BAD_REQUEST)

        totp_obj = getattr(request.user, "totp", None)
        if not totp_obj:
            return Response(
                {"detail": "2FA setup not initiated. Call GET /auth/2fa/setup/ first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if totp_obj.is_enabled:
            return Response(
                {"detail": "2FA is already enabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        totp = pyotp.TOTP(totp_obj.secret)
        if not totp.verify(code, valid_window=1):
            return Response({"detail": "Invalid TOTP code."}, status=status.HTTP_400_BAD_REQUEST)

        totp_obj.is_enabled = True
        totp_obj.save(update_fields=["is_enabled", "updated_at"])

        return Response(
            {
                "detail": "2FA enabled successfully.",
                "backup_codes": totp_obj.backup_codes,
            }
        )


class TwoFactorDisableView(APIView):
    """
    POST /api/v1/auth/2fa/disable/

    Disable 2FA.  Requires a current TOTP code (or a backup code) to confirm.

    Body: ``{"code": "123456"}``
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth / 2FA"],
        summary="Disable 2FA",
        request={
            "application/json": {
                "type": "object",
                "required": ["code"],
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Current TOTP code or a backup code.",
                        "example": "123456",
                    }
                },
            }
        },
        responses={
            200: OpenApiResponse(description="2FA disabled"),
            400: OpenApiResponse(description="Invalid code or 2FA not enabled"),
        },
    )
    def post(self, request):
        code = request.data.get("code", "").strip()
        if not code:
            return Response({"detail": "code is required."}, status=status.HTTP_400_BAD_REQUEST)

        totp_obj = getattr(request.user, "totp", None)
        if not totp_obj or not totp_obj.is_enabled:
            return Response(
                {"detail": "2FA is not enabled for this account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        totp = pyotp.TOTP(totp_obj.secret)
        valid_totp = totp.verify(code, valid_window=1)
        valid_backup = not valid_totp and totp_obj.use_backup_code(code)

        if not valid_totp and not valid_backup:
            return Response({"detail": "Invalid code."}, status=status.HTTP_400_BAD_REQUEST)

        totp_obj.delete()
        return Response({"detail": "2FA disabled successfully."})


class TwoFactorCompleteView(APIView):
    """
    POST /api/v1/auth/2fa/complete/

    Complete a 2FA-gated login.  When a user with 2FA enabled calls
    ``POST /auth/token/``, the response includes
    ``{"two_fa_required": true, "session_key": "<key>"}``.
    Submit that session key here together with the TOTP code to receive
    the final JWT pair.

    Body: ``{"session_key": "...", "code": "123456"}``
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth / 2FA"],
        summary="Complete 2FA-gated login",
        request={
            "application/json": {
                "type": "object",
                "required": ["session_key", "code"],
                "properties": {
                    "session_key": {"type": "string"},
                    "code": {
                        "type": "string",
                        "description": "TOTP code or backup code.",
                        "example": "123456",
                    },
                },
            }
        },
        responses={
            200: OpenApiResponse(description="JWT pair returned"),
            400: OpenApiResponse(description="Invalid session or code"),
        },
    )
    def post(self, request):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        session_key = request.data.get("session_key", "").strip()
        code = request.data.get("code", "").strip()

        if not session_key or not code:
            return Response(
                {"detail": "session_key and code are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = f"{_CACHE_PREFIX}{session_key}"
        user_pk = cache.get(cache_key)
        if not user_pk:
            return Response(
                {"detail": "Invalid or expired session. Please log in again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_400_BAD_REQUEST)

        totp_obj = getattr(user, "totp", None)
        if not totp_obj or not totp_obj.is_enabled:
            cache.delete(cache_key)
            return Response(
                {"detail": "2FA is not enabled for this account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        totp = pyotp.TOTP(totp_obj.secret)
        valid_totp = totp.verify(code, valid_window=1)
        valid_backup = not valid_totp and totp_obj.use_backup_code(code)

        if not valid_totp and not valid_backup:
            return Response({"detail": "Invalid TOTP code."}, status=status.HTTP_400_BAD_REQUEST)

        # Invalidate session after successful verification
        cache.delete(cache_key)

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )
