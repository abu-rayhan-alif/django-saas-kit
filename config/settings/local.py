"""Local development settings."""

from apps.common.logging_config import get_logging_config

from config.env import get_csv

from .base import *  # noqa: F403

DEBUG = True
STRUCTLOG_JSON = False
LOGGING = get_logging_config(json_logs=False)

ALLOWED_HOSTS = get_csv(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1,0.0.0.0,testserver,.localhost",
)

# ---------------------------------------------------------------------------
# CORS — allow local frontend dev server by default.
# Override CORS_ALLOWED_ORIGINS in .env for other origins.
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = get_csv(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
)
CORS_ALLOW_CREDENTIALS = True
