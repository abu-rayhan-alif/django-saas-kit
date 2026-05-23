"""Local development settings."""

from apps.common.logging_config import get_logging_config

from config.env import get_csv

from .base import *  # noqa: F403

DEBUG = True
STRUCTLOG_JSON = False
LOGGING = get_logging_config(json_logs=False)

ALLOWED_HOSTS = get_csv("ALLOWED_HOSTS", default="localhost,127.0.0.1,0.0.0.0")

REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = (  # noqa: F405
    "rest_framework.permissions.AllowAny",
)
