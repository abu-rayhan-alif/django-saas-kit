import importlib

import pytest
from decouple import UndefinedValueError


def _reload_env(monkeypatch, **env):
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    import config.env as env_module

    return importlib.reload(env_module)


def test_validate_required_settings_passes_with_env(monkeypatch):
    env_module = _reload_env(
        monkeypatch,
        SECRET_KEY="test-secret",
        DATABASE_URL="sqlite:///test.db",
        REDIS_URL="redis://localhost:6379/0",
    )
    env_module.validate_required_settings()


def test_validate_required_settings_fails_without_secret_key(monkeypatch):
    env_module = _reload_env(
        monkeypatch,
        SECRET_KEY=None,
        DATABASE_URL="sqlite:///test.db",
        REDIS_URL="redis://localhost:6379/0",
    )
    with pytest.raises(UndefinedValueError, match="SECRET_KEY"):
        env_module.validate_required_settings()


def test_get_database_url_config_sqlite(monkeypatch):
    env_module = _reload_env(
        monkeypatch,
        SECRET_KEY="test-secret",
        DATABASE_URL="sqlite:///test.db",
        REDIS_URL="redis://localhost:6379/0",
    )
    db = env_module.get_database_url_config()
    assert db["ENGINE"] == "django.db.backends.sqlite3"
