"""
Test settings — used by pytest in environments without a live PostgreSQL server.

Uses a file-backed SQLite database and locmem email backend so the full test
suite can run offline (e.g. in the local sandbox or on a dev machine with no
Docker stack).  In CI, DATABASE_URL is injected as a shell env var which
overrides the .env file, so CI always uses real PostgreSQL.
"""

import tempfile
from pathlib import Path

from .local import *  # noqa: F403

# ---------------------------------------------------------------------------
# Database — SQLite (no postgres required; works on Windows and Linux)
# ---------------------------------------------------------------------------
_TEST_DB = Path(tempfile.gettempdir()) / "django-saas-kit-test.sqlite3"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(_TEST_DB),
    }
}

# ---------------------------------------------------------------------------
# Email — capture in memory
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# ---------------------------------------------------------------------------
# Channels — in-process layer (no Redis)
# ---------------------------------------------------------------------------
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# ---------------------------------------------------------------------------
# Cache — in-process (no Redis)
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Subdomain tenant tests use *.localhost; api_client uses testserver.
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "testserver",
    ".localhost",
]
