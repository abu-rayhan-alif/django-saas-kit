import uuid

from django.db import migrations, models


def _backfill_schema_name(apps, schema_editor):
    """Copy slug → schema_name for existing tenants."""
    Tenant = apps.get_model("tenants", "Tenant")
    for tenant in Tenant.objects.all():
        tenant.schema_name = tenant.slug
        tenant.save(update_fields=["schema_name"])


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0002_tenant_is_active_alter_tenant_created_at"),
    ]

    operations = [
        # 1. Add nullable schema_name (avoids default-collision on existing rows)
        migrations.AddField(
            model_name="tenant",
            name="schema_name",
            field=models.SlugField(max_length=100, null=True),
        ),
        # 2. Backfill from slug
        migrations.RunPython(_backfill_schema_name, migrations.RunPython.noop),
        # 3. Make non-null + unique
        migrations.AlterField(
            model_name="tenant",
            name="schema_name",
            field=models.SlugField(max_length=100, unique=True),
        ),
        # 4. Domain routing table
        migrations.CreateModel(
            name="Domain",
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
                    "domain",
                    models.CharField(db_index=True, max_length=253, unique=True),
                ),
                ("is_primary", models.BooleanField(default=True)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="domains",
                        to="tenants.tenant",
                    ),
                ),
            ],
            options={
                "ordering": ["domain"],
            },
        ),
    ]
