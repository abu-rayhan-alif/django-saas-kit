"""
Settings used only for static type checking (mypy, pre-commit).

Does not require a .env file or running services.
"""

import os

os.environ.setdefault("SECRET_KEY", "mypy-only-not-for-production")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1")
os.environ.setdefault("DATABASE_URL", "sqlite:///mypy.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

from .base import *  # noqa: F403

# Avoid Redis dependency during django.setup() for type checking
CACHES = {  # noqa: F405
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
