import pytest
from django.test import Client


@pytest.fixture(autouse=True)
def celery_eager(settings):
    """Run Celery tasks synchronously in tests (no Redis broker required)."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True


@pytest.fixture(autouse=True)
def locmem_email(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture
def api_client() -> Client:
    return Client()
