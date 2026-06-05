from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from rest_framework import serializers

from apps.users.models import UserProfile

User = get_user_model()


class UserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, default="")
    last_name = serializers.CharField(max_length=150, required=False, default="")


class UserSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "display_name")
        read_only_fields = fields

    def get_display_name(self, obj: AbstractUser) -> str:
        from services.users import UserService

        return UserService.get_display_name(obj)


class UserProfileSerializer(serializers.ModelSerializer):
    """Read/write serializer for UserProfile.  Used by GET/PATCH /users/me/profile/."""

    avatar_url = serializers.ReadOnlyField()

    class Meta:
        model = UserProfile
        fields = ("bio", "phone", "timezone", "avatar", "avatar_url", "updated_at")
        read_only_fields = ("avatar_url", "updated_at")
        extra_kwargs = {
            "avatar": {"write_only": True, "required": False},
        }

    def validate_timezone(self, value: str) -> str:
        from zoneinfo import ZoneInfoNotFoundError, available_timezones

        if value and value not in available_timezones():
            raise serializers.ValidationError(f"Unknown timezone: {value!r}")
        return value


class UserWithProfileSerializer(serializers.ModelSerializer):
    """User + embedded profile — returned by GET /users/me/."""

    id = serializers.CharField(read_only=True)
    display_name = serializers.SerializerMethodField()
    profile = UserProfileSerializer(read_only=True)
    two_fa_enabled = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "profile",
            "two_fa_enabled",
        )
        read_only_fields = fields

    def get_display_name(self, obj: AbstractUser) -> str:
        from services.users import UserService

        return UserService.get_display_name(obj)

    def get_two_fa_enabled(self, obj: AbstractUser) -> bool:
        totp = getattr(obj, "totp", None)
        return bool(totp and totp.is_enabled)
