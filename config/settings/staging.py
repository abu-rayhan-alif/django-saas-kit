"""Staging environment — production-like with selective relaxations."""

from config.env import get_bool

from .prod import *  # noqa: F403

DEBUG = get_bool("DEBUG", default=False)
SECURE_SSL_REDIRECT = get_bool("SECURE_SSL_REDIRECT", default=False)
