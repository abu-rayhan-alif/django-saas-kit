"""
Root conftest — loaded before any test collection or Django setup.
"""

import os

import pytest
from django.test import Client


def pytest_configure(config):
    """Seed required env vars *before* Django loads settings.

    validate_required_settings() checks os.environ exclusively so that CI
    works without a .env file.  In local dev the .env file provides these at
    shell level; in the test harness we back-fill safe defaults here.
    """
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/saas-test.sqlite3")


@pytest.fixture
def api_client() -> Client:
    return Client()


@pytest.fixture(autouse=True)
def locmem_cache(settings):
    """Use in-memory cache for all tests — avoids Redis dependency."""
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }


@pytest.fixture(autouse=True)
def disable_throttling():
    """Patch APIView.throttle_classes directly — settings-based approach fails
    because DRF sets throttle_classes as a class attribute at import time."""
    from rest_framework.views import APIView

    original = APIView.throttle_classes
    APIView.throttle_classes = []
    yield
    APIView.throttle_classes = original


@pytest.fixture
def with_throttling():
    """Re-enable throttle classes for tests that specifically test rate limiting.
    Must be listed as an explicit parameter on the test function.
    Runs AFTER disable_throttling (autouse), so it overrides it for this test.
    """
    from apps.common.throttling import AnonRateThrottle, LoginRateThrottle, UserRateThrottle
    from rest_framework.views import APIView

    APIView.throttle_classes = [AnonRateThrottle, UserRateThrottle, LoginRateThrottle]
    yield
    APIView.throttle_classes = []


@pytest.fixture(autouse=True)
def celery_eager(settings):
    """Run Celery tasks synchronously in tests — avoids broker/Redis dependency."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.CELERY_RESULT_BACKEND = "cache+memory://"
    settings.CELERY_CACHE_BACKEND = "django-cache"
