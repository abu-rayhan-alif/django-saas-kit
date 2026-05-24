"""Management command: erase personal data for a given user (GDPR Art. 17).

Usage
-----
    # Anonymize (default) — keeps the user row, wipes all PII:
    python manage.py delete_user_data <user_id>

    # Hard-delete — removes the user row entirely:
    python manage.py delete_user_data <user_id> --hard-delete

    # Skip the confirmation prompt (for scripts/CI):
    python manage.py delete_user_data <user_id> --no-input
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from services.users.gdpr_service import GDPRService

User = get_user_model()


class Command(BaseCommand):
    help = "Erase personal data for a user (GDPR Art. 17 right to be forgotten)."

    def add_arguments(self, parser):
        parser.add_argument(
            "user_id",
            help="Primary key of the user whose data should be erased.",
        )
        parser.add_argument(
            "--hard-delete",
            action="store_true",
            default=False,
            dest="hard_delete",
            help=(
                "Permanently delete the user row and all child records. "
                "Default behaviour is to anonymise the user row in-place."
            ),
        )
        parser.add_argument(
            "--no-input",
            action="store_true",
            default=False,
            dest="no_input",
            help="Skip the confirmation prompt (use in scripts).",
        )

    def handle(self, *args, **options):
        user_id = options["user_id"]
        hard_delete = options["hard_delete"]
        no_input = options["no_input"]

        try:
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError) as exc:
            raise CommandError(f"No user found with id '{user_id}'.") from exc

        mode_label = "HARD DELETE (permanent removal)" if hard_delete else "ANONYMIZE (PII wipe)"

        self.stdout.write(f"User   : {user.username} (id={user.pk})")
        self.stdout.write(f"Email  : {user.email}")
        self.stdout.write(f"Mode   : {mode_label}")
        self.stdout.write("")

        if not no_input:
            confirm = input("Type 'yes' to confirm erasure, or anything else to cancel: ")
            if confirm.strip().lower() != "yes":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        if hard_delete:
            result = GDPRService.hard_delete(user)
        else:
            result = GDPRService.anonymize(user)

        self.stdout.write(self.style.SUCCESS("Erasure complete."))
        self.stdout.write(f"  Notifications deleted : {result.notifications_deleted}")
        self.stdout.write(f"  Roles deleted         : {result.roles_deleted}")
        self.stdout.write(f"  JWT tokens revoked    : {result.tokens_deleted}")
        self.stdout.write(f"  Mode                  : {result.mode}")
