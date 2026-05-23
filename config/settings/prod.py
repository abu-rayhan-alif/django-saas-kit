"""Production settings — hardened defaults."""

from django.core.exceptions import ImproperlyConfigured

from config.env import get_bool, get_csv

from .base import *  # noqa: F403

DEBUG = False

ALLOWED_HOSTS = get_csv("ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS is required in production. "
        "Set a comma-separated list of hostnames in the environment."
    )

# Security
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = get_bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Stricter logging in production
LOGGING["root"]["level"] = "WARNING"  # type: ignore[index]  # noqa: F405
