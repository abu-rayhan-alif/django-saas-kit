from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.rbac.models import RoleChoices, UserTenantRole

User = get_user_model()


class UserTenantRoleSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)

    class Meta:
        model = UserTenantRole
        fields = ("id", "username", "tenant_name", "role", "created_at")
        read_only_fields = fields


class RoleAssignSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(help_text="PK of the user to assign the role to.")
    role = serializers.ChoiceField(
        choices=RoleChoices.choices,
        help_text="One of: owner, admin, member.",
    )

    def validate_user_id(self, value: int):
        try:
            return User.objects.get(pk=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")


class RoleRevokeSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(help_text="PK of the user whose role to revoke.")

    def validate_user_id(self, value: int):
        try:
            return User.objects.get(pk=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
