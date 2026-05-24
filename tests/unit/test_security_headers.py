"""SAAS-701 -- CORS, CSP, and production security settings."""

from __future__ import annotations

import importlib
import sys


def test_cors_preflight_allows_configured_origin(api_client, settings):
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]
    response = api_client.options(
        "/api/v1/users/",
        HTTP_ORIGIN="http://localhost:3000",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
    )
    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == "http://localhost:3000"


def test_cors_preflight_rejects_unknown_origin(api_client, settings):
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]
    response = api_client.options(
        "/api/v1/users/",
        HTTP_ORIGIN="https://evil.example.com",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
    )
    assert "Access-Control-Allow-Origin" not in response


def test_csp_header_when_policy_configured(api_client, settings):
    settings.CONTENT_SECURITY_POLICY = "default-src 'self'; frame-ancestors 'none'"
    response = api_client.get("/health/")
    assert response["Content-Security-Policy"] == "default-src 'self'; frame-ancestors 'none'"


def test_no_csp_header_when_policy_empty(api_client, settings):
    settings.CONTENT_SECURITY_POLICY = ""
    response = api_client.get("/health/")
    assert "Content-Security-Policy" not in response


def test_prod_settings_security(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ALLOWED_HOSTS", "api.example.com")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")

    for mod in list(sys.modules):
        if mod.startswith("config.settings"):
            sys.modules.pop(mod, None)

    prod = importlib.import_module("config.settings.prod")

    assert prod.SECURE_SSL_REDIRECT is True
    assert prod.ALLOWED_HOSTS == ["api.example.com"]
    assert prod.SECURE_HSTS_SECONDS > 0
    assert prod.X_FRAME_OPTIONS == "DENY"
    assert prod.CONTENT_SECURITY_POLICY
    assert "frame-ancestors" in prod.CONTENT_SECURITY_POLICY
    assert prod.CORS_ALLOWED_ORIGINS == ["https://app.example.com"]


def test_allowed_hosts_from_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ALLOWED_HOSTS", "a.example.com,b.example.com")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")

    for mod in list(sys.modules):
        if mod.startswith("config.settings"):
            sys.modules.pop(mod, None)

    prod = importlib.import_module("config.settings.prod")
    assert prod.ALLOWED_HOSTS == ["a.example.com", "b.example.com"]
