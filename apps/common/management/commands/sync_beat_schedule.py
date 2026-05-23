"""Register periodic tasks in django-celery-beat (idempotent)."""

from django.conf import settings
from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask


class Command(BaseCommand):
    help = "Sync Celery Beat periodic tasks from config/celery.py (SAAS-501)."

    def handle(self, *args, **options):
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="3",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
            timezone=str(settings.TIME_ZONE),
        )
        task, created = PeriodicTask.objects.update_or_create(
            name="cleanup-expired-tokens-daily",
            defaults={
                "task": "apps.authentication.tasks.cleanup_expired_tokens",
                "crontab": schedule,
                "enabled": True,
                "description": "Flush expired JWT blacklist tokens (daily 03:00 UTC)",
            },
        )
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} periodic task: {task.name}"))
