from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor_email",
            "action",
            "action_display",
            "resource_type",
            "resource_id",
            "metadata",
            "ip_address",
            "timestamp",
        ]
        read_only_fields = fields
