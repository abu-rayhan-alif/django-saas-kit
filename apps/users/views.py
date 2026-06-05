from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from services.exceptions import ConflictServiceError, ValidationServiceError
from services.users import CreateUserInput, UserService

from apps.rbac.permissions import HasRolePermission
from apps.users.filters import UserFilter
from apps.users.models import UserProfile
from apps.users.serializers import (
    UserCreateSerializer,
    UserProfileSerializer,
    UserSerializer,
    UserWithProfileSerializer,
)

User = get_user_model()


class UserCreateView(APIView):
    """HTTP adapter — delegates user creation to UserService."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Users"],
        request=UserCreateSerializer,
        responses={201: UserSerializer},
        summary="Register a new user",
    )
    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = UserService.create_user(
                CreateUserInput(**serializer.validated_data),
            )
        except ValidationServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ConflictServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class UserListView(generics.ListAPIView):
    """
    Paginated, filterable list of all users. Admin only.

    Filtering  — is_active, date_joined_after, date_joined_before
    Search     — ?search= across username, email, first_name, last_name
    Ordering   — ?ordering= date_joined | username | email  (prefix - for desc)
    """

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_roles = ["owner", "admin"]
    filterset_class = UserFilter
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["date_joined", "username", "email"]
    ordering = ["-date_joined"]

    @extend_schema(
        tags=["Users"],
        summary="List users",
        description="Paginated, filterable list of all users. Admin only.",
        responses={200: UserSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        if tenant is None:
            return User.objects.none()
        return User.objects.filter(tenant_roles__tenant=tenant).distinct().order_by("-date_joined")


class MeView(APIView):
    """
    GET /api/v1/users/me/

    Return the authenticated user's full profile (user fields + profile extension + 2FA status).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Users"],
        summary="Get current user (with profile)",
        responses={200: UserWithProfileSerializer},
    )
    def get(self, request):
        # Ensure profile row exists
        UserProfile.objects.get_or_create(user=request.user)
        serializer = UserWithProfileSerializer(request.user)
        return Response(serializer.data)


class ProfileView(APIView):
    """
    GET  /api/v1/users/me/profile/  — retrieve profile fields
    PATCH /api/v1/users/me/profile/ — update bio, phone, timezone, avatar
    """

    permission_classes = [IsAuthenticated]

    def _get_profile(self, user):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return profile

    @extend_schema(
        tags=["Users"],
        summary="Get profile",
        responses={200: UserProfileSerializer},
    )
    def get(self, request):
        serializer = UserProfileSerializer(self._get_profile(request.user))
        return Response(serializer.data)

    @extend_schema(
        tags=["Users"],
        summary="Update profile (partial)",
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer},
    )
    def patch(self, request):
        profile = self._get_profile(request.user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        tags=["Users"],
        summary="Replace profile (full update)",
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer},
    )
    def put(self, request):
        profile = self._get_profile(request.user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        tags=["Users"],
        summary="Delete avatar",
        responses={204: None},
    )
    def delete(self, request):
        """DELETE /api/v1/users/me/profile/avatar/ — clears the avatar field."""
        profile = self._get_profile(request.user)
        if profile.avatar:
            profile.avatar.delete(save=False)
            profile.avatar = None
            profile.save(update_fields=["avatar", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)
