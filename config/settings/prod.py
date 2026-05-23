"""Production settings — hardened defaults."""

from apps.common.logging_config import get_logging_config
from django.core.exceptions import ImproperlyConfigured

from config.env import get_csv, get_str
from config.settings.security import DEFAULT_CONTENT_SECURITY_POLICY, HSTS_SECONDS

from .base import *  # noqa: F403

STRUCTLOG_JSON = True
LOGGING = get_logging_config(json_logs=True)

DEBUG = False

ALLOWED_HOSTS = get_csv("ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS is required in production. "
        "Set a comma-separated list of hostnames in the environment."
    )

# Security (SAAS-701)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = HSTS_SECONDS
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CONTENT_SECURITY_POLICY = get_str(
    "CONTENT_SECURITY_POLICY",
    default=DEFAULT_CONTENT_SECURITY_POLICY,
).strip()

# Stricter logging in production
LOGGING["root"]["level"] = "WARNING"  # type: ignore[index]  # noqa: F405
