from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from services.exceptions import ConflictServiceError, ValidationServiceError
from services.users import CreateUserInput, UserService

from apps.users.filters import UserFilter
from apps.users.serializers import UserCreateSerializer, UserSerializer

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
    permission_classes = [IsAdminUser]
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
        return (
            User.objects.filter(tenant_roles__tenant=tenant)
            .distinct()
            .order_by("-date_joined")
        )
