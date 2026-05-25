import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Plan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("stripe_price_id", models.CharField(blank=True, default="", max_length=255)),
                (
                    "max_members",
                    models.PositiveIntegerField(
                        default=5,
                        help_text="Maximum number of members per tenant. 0 = unlimited.",
                    ),
                ),
                (
                    "max_storage_mb",
                    models.PositiveIntegerField(
                        default=1024,
                        help_text="Storage quota in MiB. 0 = unlimited.",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="subscription",
            name="plan",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="subscriptions",
                to="billing.plan",
            ),
        ),
    ]
