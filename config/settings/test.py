"""
Test settings — used by pytest in environments without a live PostgreSQL server.

Uses an in-memory SQLite database and locmem email backend so the full test
suite can run offline (e.g. in the local sandbox or on a dev machine with no
Docker stack).  In CI, DATABASE_URL is injected as a shell env var which
overrides the .env file, so CI always uses real PostgreSQL.
"""

from .local import *  # noqa: F403

# ---------------------------------------------------------------------------
# Database — SQLite (no postgres required)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "/tmp/saas-test.sqlite3",
        "TEST": {"NAME": "/tmp/saas-test.sqlite3"},
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
