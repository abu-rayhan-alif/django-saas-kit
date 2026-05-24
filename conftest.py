"""
Root conftest.py — loaded before pytest-django initialises Django settings.

Sets required environment variables using setdefault so that they can still
be overridden by the calling shell (e.g. DATABASE_URL in CI).
"""

import os


def pytest_configure(config):  # noqa: ARG001
    """Inject required env vars before Django loads settings.

    validate_required_settings() reads os.environ exclusively so CI doesn't
    need a .env file.  Here we back-fill safe defaults for local test runs.
    """
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/saas-test.sqlite3")
