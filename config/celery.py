"""
Celery application entry-point.

Configuration is loaded from Django settings (``CELERY_*`` keys):

- Broker:  ``CELERY_BROKER_URL``  (default: ``REDIS_URL``)
- Backend: ``CELERY_RESULT_BACKEND``
- Tasks:   auto-discovered from ``tasks.py`` in each ``INSTALLED_APPS`` entry
- Beat:    daily ``flushexpiredtokens`` + any tasks registered via django-celery-beat
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("django_saas_kit")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
