"""
Root conftest — loaded before any test collection or Django setup.
"""

import os
import tempfile
from pathlib import Path

import pytest
from django.test import Client

_TEST_DB = Path(tempfile.gettempdir()) / "django-saas-kit-test.sqlite3"


def pytest_configure(config):
    """Seed required env vars *before* Django loads settings.

    validate_required_settings() checks os.environ exclusively so that CI
    works without a .env file.  In local dev the .env file provides these at
    shell level; in the test harness we back-fill safe defaults here.
    """
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TEST_DB.as_posix()}")


@pytest.fixture(autouse=True)
def ensure_testserver_domain(db):
    """Map Django test client host to a tenant so /api/v1/* requests pass TenantMiddleware.

    Also wires a post_save signal so every User created during the test is given
    a role in the test tenant.  Staff/superusers get ADMIN; regular users get MEMBER.
    This lets endpoints that scope their queryset by request.tenant (e.g. UserListView)
    return results in the default testserver environment without each test needing to
    set up roles manually.  The signal is suppressed when tests.suppress_auto_tenant.active
    is True (set by the services conftest) or when DemoSeedService.seed() is running.
    Domain-specific tests (alpha.localhost, beta.localhost) are unaffected because
    they query against their own tenant, not the test tenant.
    """
    from django.contrib.auth import get_user_model
    from django.db.models.signals import post_save

    from apps.rbac.models import RoleChoices, UserTenantRole
    from apps.tenants.models import Domain, Tenant
    from tests import suppress_auto_tenant as _suppress

    tenant, _ = Tenant.objects.get_or_create(
        slug="test",
        defaults={"name": "Test Tenant", "schema_name": "test"},
    )
    Domain.objects.update_or_create(
        tenant=tenant,
        domain="testserver",
        defaults={"is_primary": True},
    )

    User = get_user_model()

    def _assign_to_test_tenant(sender, instance, created, **kwargs):
        from services.demo.seed_service import _seeding  # noqa: PLC0415

        if created and not getattr(_suppress, "active", False) and not getattr(_seeding, "active", False):
            role = RoleChoices.ADMIN if (instance.is_staff or instance.is_superuser) else RoleChoices.MEMBER
            UserTenantRole.objects.get_or_create(
                user=instance,
                tenant=tenant,
                defaults={"role": role},
            )

    post_save.connect(_assign_to_test_tenant, sender=User, weak=False)
    yield
    post_save.disconnect(_assign_to_test_tenant, sender=User)


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
def clear_throttle_cache():
    """Prevent login throttle state leaking between tests."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def disable_throttling():
    """Patch throttle_classes on APIView and the login token view."""
    from apps.authentication.views import ThrottledTokenObtainPairView
    from rest_framework.views import APIView

    saved = {
        APIView: APIView.throttle_classes,
        ThrottledTokenObtainPairView: ThrottledTokenObtainPairView.throttle_classes,
    }
    APIView.throttle_classes = []
    ThrottledTokenObtainPairView.throttle_classes = []
    yield
    APIView.throttle_classes = saved[APIView]
    ThrottledTokenObtainPairView.throttle_classes = saved[ThrottledTokenObtainPairView]


@pytest.fixture
def with_throttling():
    """Re-enable throttle classes for tests that specifically test rate limiting.
    Must be listed as an explicit parameter on the test function.
    Runs AFTER disable_throttling (autouse), so it overrides it for this test.
    """
    from apps.authentication.views import ThrottledTokenObtainPairView
    from apps.common.throttling import AnonRateThrottle, LoginRateThrottle, UserRateThrottle
    from rest_framework.views import APIView

    APIView.throttle_classes = [AnonRateThrottle, UserRateThrottle, LoginRateThrottle]
    ThrottledTokenObtainPairView.throttle_classes = [LoginRateThrottle]
    yield
    APIView.throttle_classes = []
    ThrottledTokenObtainPairView.throttle_classes = []


@pytest.fixture(autouse=True)
def celery_eager(settings):
    """Run Celery tasks synchronously in tests — avoids broker/Redis dependency."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.CELERY_RESULT_BACKEND = "cache+memory://"
    settings.CELERY_CACHE_BACKEND = "django-cache"
