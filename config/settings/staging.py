"""Staging environment settings."""

from .prod import *  # noqa: F403

DEBUG = env.bool("DEBUG", default=False)  # noqa: F405
