from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, default="")
    last_name = serializers.CharField(max_length=150, required=False, default="")


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="Email address associated with the account.")


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(help_text="Base64-encoded user ID from the reset email.")
    token = serializers.CharField(help_text="Password-reset token from the reset email.")
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="New password to set.",
    )
