"""Local development settings."""

from .base import *  # noqa: F403

DEBUG = True

REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = (  # noqa: F405
    "rest_framework.permissions.AllowAny",
)
