"""Local development settings."""

from config.env import get_csv

from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = get_csv("ALLOWED_HOSTS", default="localhost,127.0.0.1,0.0.0.0")

REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = (  # noqa: F405
    "rest_framework.permissions.AllowAny",
)
