"""
Celery application for django-saas-kit (SAAS-501).

- Broker: Redis (``CELERY_BROKER_URL``)
- Results: Redis (``CELERY_RESULT_BACKEND``)
- Tasks: auto-discovered from ``tasks.py`` in each ``INSTALLED_APPS`` entry
- Beat: daily ``cleanup_expired_tokens`` (see ``beat_schedule``)
"""

import os

from celery.schedules import crontab

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("django_saas_kit")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Periodic tasks (django-celery-beat DatabaseScheduler merges this schedule)
app.conf.beat_schedule = {
    "cleanup-expired-tokens-daily": {
        "task": "apps.authentication.tasks.cleanup_expired_tokens",
        "schedule": crontab(hour=3, minute=0),
        "options": {"expires": 60 * 60},
    },
}
