import importlib
import sys

import pytest


@pytest.fixture
def env_vars(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")


def _reload_settings(module_name: str):
    for mod in list(sys.modules):
        if mod.startswith("config.settings") or mod == "config.env":
            sys.modules.pop(mod, None)
    return importlib.import_module(module_name)


def test_wsgi_application_loads(env_vars):
    wsgi = importlib.import_module("config.wsgi")
    assert wsgi.application is not None


def test_asgi_application_loads(env_vars):
    asgi = importlib.import_module("config.asgi")
    assert asgi.application is not None


def test_prod_settings_load(env_vars):
    settings = _reload_settings("config.settings.prod")
    assert settings.DEBUG is False
    assert "localhost" in settings.ALLOWED_HOSTS
    assert settings.CORS_ALLOWED_ORIGINS == ["http://localhost:3000"]


def test_staging_settings_load(env_vars):
    settings = _reload_settings("config.settings.staging")
    assert hasattr(settings, "SECRET_KEY")
    assert settings.SECURE_SSL_REDIRECT is False


def test_mypy_settings_load_without_env_file():
    settings = importlib.import_module("config.settings.mypy")
    assert settings.SECRET_KEY
    assert settings.CACHES["default"]["BACKEND"].endswith("LocMemCache")


def test_prod_settings_require_allowed_hosts(monkeypatch, env_vars):
    monkeypatch.setenv("ALLOWED_HOSTS", "")
    from django.core.exceptions import ImproperlyConfigured

    with pytest.raises(ImproperlyConfigured, match="ALLOWED_HOSTS"):
        _reload_settings("config.settings.prod")


def test_prod_settings_require_cors_origins(monkeypatch, env_vars):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    from django.core.exceptions import ImproperlyConfigured

    with pytest.raises(ImproperlyConfigured, match="CORS_ALLOWED_ORIGINS"):
        _reload_settings("config.settings.prod")
