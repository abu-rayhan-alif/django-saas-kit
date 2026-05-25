"""
Environment variables via python-decouple.

Install ``python-decouple`` (not the unrelated ``decouple`` package on PyPI).

Required variables raise ``UndefinedValueError`` at import time when missing.
"""

from pathlib import Path
from typing import Any, cast

import dj_database_url
from decouple import AutoConfig, Csv, UndefinedValueError, undefined

BASE_DIR = Path(__file__).resolve().parent.parent

_config = AutoConfig(search_path=BASE_DIR)

REQUIRED_VARS = (
    "SECRET_KEY",
    "DATABASE_URL",
    "REDIS_URL",
)


def get_str(key: str, *, default=undefined, required: bool = False) -> str:
    if required:
        return _config(key)
    return _config(key, default=default)


def get_bool(key: str, *, default: bool = False) -> bool:
    return _config(key, default=default, cast=bool)


def get_int(key: str, *, default: int | None = None) -> int:
    if default is None:
        return _config(key, cast=int)
    return _config(key, default=default, cast=int)


def get_csv(key: str, *, default: str = "") -> list[str]:
    return _config(key, default=default, cast=Csv())


def get_database_url_config() -> dict[str, Any]:
    url = get_str("DATABASE_URL", required=True)
    return cast(dict[str, Any], dj_database_url.parse(url, conn_max_age=600))


_MIN_SECRET_KEY_LENGTH = 50


def validate_required_settings() -> None:
    """Eagerly resolve required env vars so startup fails fast."""
    missing: list[str] = []
    for key in REQUIRED_VARS:
        try:
            value = _config(key)
            if not str(value).strip():
                missing.append(key)
        except UndefinedValueError:
            missing.append(key)
    if missing:
        raise UndefinedValueError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            "Copy .env.example to .env and set all required values."
        )
    try:
        secret_key = str(_config("SECRET_KEY")).strip()
        if len(secret_key) < _MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"SECRET_KEY must be at least {_MIN_SECRET_KEY_LENGTH} characters. "
                "Generate one with: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
            )
    except UndefinedValueError:
        pass  # already caught above


__all__ = [
    "BASE_DIR",
    "REQUIRED_VARS",
    "UndefinedValueError",
    "get_bool",
    "get_csv",
    "get_database_url_config",
    "get_int",
    "get_str",
    "validate_required_settings",
]
