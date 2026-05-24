"""Production settings -- hardened defaults."""

from apps.common.logging_config import get_logging_config
from django.core.exceptions import ImproperlyConfigured

from config.env import get_bool, get_csv, get_str
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
X_FRAME_OPTIONS = "DENY"
CONTENT_SECURITY_POLICY = DEFAULT_CONTENT_SECURITY_POLICY

# Referrer policy
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# CORS -- must be explicitly configured in production via env var.
CORS_ALLOWED_ORIGINS = get_csv("CORS_ALLOWED_ORIGINS", default="")
CORS_ALLOW_CREDENTIALS = get_bool("CORS_ALLOW_CREDENTIALS", default=False)
if not CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured(
        "CORS_ALLOWED_ORIGINS is required in production. "
        "Set a comma-separated list of allowed origins, e.g. https://app.example.com"
    )

# Sentry (optional -- gracefully skipped when SENTRY_DSN is unset)
_sentry_dsn = get_str("SENTRY_DSN", default="")
if _sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=_sentry_dsn,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
