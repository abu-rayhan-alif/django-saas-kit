import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("tenants", "0003_tenant_schema_name_domain"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "actor_email",
                    models.EmailField(blank=True, max_length=254),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("login", "Login"),
                            ("logout", "Logout"),
                            ("login_failed", "Login Failed"),
                            ("password_reset_requested", "Password Reset Requested"),
                            ("password_reset_confirmed", "Password Reset Confirmed"),
                            ("user_registered", "User Registered"),
                            ("user_deleted", "User Deleted (GDPR)"),
                            ("role_assigned", "Role Assigned"),
                            ("role_revoked", "Role Revoked"),
                            ("member_invited", "Member Invited"),
                            ("invitation_accepted", "Invitation Accepted"),
                            ("invitation_revoked", "Invitation Revoked"),
                            ("subscription_created", "Subscription Created"),
                            ("subscription_updated", "Subscription Updated"),
                            ("subscription_canceled", "Subscription Canceled"),
                            ("payment_succeeded", "Payment Succeeded"),
                            ("payment_failed", "Payment Failed"),
                        ],
                        db_index=True,
                        max_length=50,
                    ),
                ),
                ("resource_type", models.CharField(blank=True, max_length=100)),
                ("resource_id", models.CharField(blank=True, max_length=255)),
                ("metadata", models.JSONField(default=dict)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audit_logs",
                        to="tenants.tenant",
                    ),
                ),
            ],
            options={
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["tenant", "timestamp"], name="audit_tenant_ts_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["tenant", "action"], name="audit_tenant_action_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["actor", "timestamp"], name="audit_actor_ts_idx"),
        ),
    ]
