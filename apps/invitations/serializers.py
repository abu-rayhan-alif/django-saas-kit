from rest_framework import serializers

from apps.invitations.models import TenantInvitation
from apps.rbac.models import RoleChoices


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=RoleChoices.choices,
        default=RoleChoices.MEMBER,
    )


class InvitationSerializer(serializers.ModelSerializer):
    invited_by_email = serializers.EmailField(source="invited_by.email", read_only=True)
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = TenantInvitation
        fields = [
            "id",
            "tenant_name",
            "email",
            "role",
            "status",
            "invited_by_email",
            "expires_at",
            "created_at",
            "is_expired",
        ]
        read_only_fields = fields


class InvitationAcceptSerializer(serializers.Serializer):
    """Empty body — the token in the URL is all that's needed."""
    pass
