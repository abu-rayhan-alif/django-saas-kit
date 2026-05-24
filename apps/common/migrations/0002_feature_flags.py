"""
Data migration — seed the built-in feature flags.

Creates the ``new_dashboard`` flag in an *off* state so it can be toggled
from the Django admin without any code changes.

Depends on ``waffle``'s own schema migrations so the ``waffle_flag`` table
is guaranteed to exist before we insert rows.
"""

from django.db import migrations


def create_feature_flags(apps, schema_editor):
    """Create built-in flags with safe defaults (all off)."""
    Flag = apps.get_model("waffle", "Flag")

    Flag.objects.get_or_create(
        name="new_dashboard",
        defaults={
            # everyone=None  → flag is off for all users by default.
            # Set to True in /admin/waffle/flag/ to enable for everyone,
            # or add specific users / groups there.
            "everyone": None,
            "note": (
                "SAAS-903 — example feature flag. "
                "Enable in /admin/waffle/flag/ to roll out the new dashboard UI."
            ),
        },
    )


def remove_feature_flags(apps, schema_editor):
    """Reverse: remove the flags created by this migration."""
    Flag = apps.get_model("waffle", "Flag")
    Flag.objects.filter(name="new_dashboard").delete()


class Migration(migrations.Migration):
    dependencies = [
        # waffle's schema must exist before we insert flag rows
        ("waffle", "0004_update_everyone_nullbooleanfield"),
        # previous common migration
        ("common", "0001_base_model"),
    ]

    operations = [
        migrations.RunPython(create_feature_flags, reverse_code=remove_feature_flags),
    ]
