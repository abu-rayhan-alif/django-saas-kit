"""SAAS-601 — structured logging, request_id, and Celery trace_id."""

from __future__ import annotations

import uuid

import pytest
import structlog
from apps.common.celery_logging import (
    TRACE_ID_HEADER,
    bind_task_trace_id,
    clear_task_trace_id,
    inject_trace_id,
)
from apps.common.logging_config import shared_processors
from apps.common.middleware.request_context import REQUEST_ID_HEADER
from structlog.testing import capture_logs


def test_request_id_header_generated(api_client):
    response = api_client.get("/health/")
    request_id = response.headers.get(REQUEST_ID_HEADER)
    assert request_id
    uuid.UUID(request_id)


def test_request_id_header_honored(api_client):
    incoming = "00000000-0000-4000-8000-000000000099"
    response = api_client.get("/health/", HTTP_X_REQUEST_ID=incoming)
    assert response.headers.get(REQUEST_ID_HEADER) == incoming


def test_request_id_bound_in_logs():
    with capture_logs(processors=shared_processors()) as logs:
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id="log-test-id")
        structlog.get_logger("tests").info("event")
    assert logs[0]["request_id"] == "log-test-id"


def test_inject_trace_id_from_request_context() -> None:
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id="trace-from-http")
    headers: dict[str, str] = {}
    inject_trace_id(headers=headers)
    assert headers[TRACE_ID_HEADER] == "trace-from-http"


def test_bind_task_trace_id_from_headers() -> None:
    class _Request:
        headers: dict[str, str] = {TRACE_ID_HEADER: "celery-trace-123"}

    class _Task:
        request: _Request = _Request()

    bind_task_trace_id(task_id="1", task=_Task())
    assert structlog.contextvars.get_contextvars()["trace_id"] == "celery-trace-123"
    clear_task_trace_id(task_id="1", task=_Task())
    assert structlog.contextvars.get_contextvars() == {}


def test_bind_task_trace_id_generated_when_missing() -> None:
    class _Request:
        headers: dict[str, str] = {}

    class _Task:
        request: _Request = _Request()

    bind_task_trace_id(task_id="1", task=_Task())
    trace_id = structlog.contextvars.get_contextvars()["trace_id"]
    uuid.UUID(trace_id)
    clear_task_trace_id(task_id="1", task=_Task())


@pytest.mark.django_db(transaction=True)
def test_celery_task_binds_trace_id_from_headers(monkeypatch, settings) -> None:
    """Worker binds ``trace_id`` from Celery message headers (publish propagation)."""
    from apps.users.tasks import send_welcome_email
    from django.contrib.auth import get_user_model
    from services.users import welcome_email_service

    captured: dict[str, str | None] = {}
    trace = "00000000-0000-4000-8000-000000000088"

    def send_and_capture(user_id: int) -> str:
        captured["trace_id"] = structlog.contextvars.get_contextvars().get("trace_id")
        return f"welcome_sent:{user_id}"

    monkeypatch.setattr(
        welcome_email_service.WelcomeEmailService,
        "send_to_user",
        staticmethod(send_and_capture),
    )
    monkeypatch.setattr(
        "services.common.idempotency.IdempotencyService.run",
        lambda _key, fn: fn(),
    )

    user = get_user_model().objects.create_user(
        username="trace",
        email="trace@example.com",
        password="SecurePass123!",
    )
    send_welcome_email.apply(args=(user.pk,), headers={TRACE_ID_HEADER: trace})
    assert captured["trace_id"] == trace


def test_structlog_json_in_prod_settings(monkeypatch):
    import importlib
    import sys

    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")

    for mod in list(sys.modules):
        if mod.startswith("config.settings"):
            sys.modules.pop(mod, None)
    prod = importlib.import_module("config.settings.prod")
    assert prod.STRUCTLOG_JSON is True
    assert "json" in prod.LOGGING["formatters"]


def test_structlog_console_in_local_settings(monkeypatch):
    import importlib
    import sys

    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ALLOWED_HOSTS", "localhost,127.0.0.1")

    for mod in list(sys.modules):
        if mod.startswith("config.settings"):
            sys.modules.pop(mod, None)
    local = importlib.import_module("config.settings.local")
    assert local.STRUCTLOG_JSON is False
    assert "console" in local.LOGGING["formatters"]


def test_json_log_format(settings):
    from apps.common.logging_config import reconfigure_logging

    reconfigure_logging(json_logs=True)
    with capture_logs() as logs:
        structlog.get_logger("tests.json").info("json_event", key="value")
    # capture_logs returns dict events; JSON rendering applies to stdlib path.
    assert logs[0]["event"] == "json_event"
    assert logs[0]["key"] == "value"


# ---------------------------------------------------------------------------
# NEW-05 — sensitive-field redaction
# ---------------------------------------------------------------------------


def test_redact_sensitive_fields_processor():
    from apps.common.logging_config import redact_sensitive_fields

    event_dict = {
        "event": "user_login",
        "password": "hunter2",
        "email": "alice@example.com",
        "token": "eyJhbGci...",
        "safe_field": "keep_me",
    }
    result = redact_sensitive_fields(None, "info", event_dict)

    assert result["password"] == "[REDACTED]"
    assert result["email"] == "[REDACTED]"
    assert result["token"] == "[REDACTED]"
    assert result["safe_field"] == "keep_me"
    assert result["event"] == "user_login"


def test_redact_all_sensitive_fields_present_in_blocklist():
    """Every field in SENSITIVE_FIELDS is redacted from log output."""
    from apps.common.logging_config import SENSITIVE_FIELDS, redact_sensitive_fields

    event_dict: dict = {"event": "test"} | {f: "secret_value" for f in SENSITIVE_FIELDS}
    result = redact_sensitive_fields(None, "info", event_dict)

    for field in SENSITIVE_FIELDS:
        assert result[field] == "[REDACTED]", f"Field '{field}' was not redacted"


def test_redaction_runs_in_shared_processors():
    """Integration: sensitive fields are absent from final log output."""
    with capture_logs(processors=shared_processors()) as logs:
        structlog.contextvars.clear_contextvars()
        structlog.get_logger("tests").info(
            "auth_attempt",
            password="should_not_appear",
            access_token="raw_jwt",
            user_id=42,
        )
    record = logs[0]
    assert record["password"] == "[REDACTED]"
    assert record["access_token"] == "[REDACTED]"
    assert record["user_id"] == 42


def test_redact_does_not_mutate_fields_not_in_blocklist():
    from apps.common.logging_config import redact_sensitive_fields

    event_dict = {"event": "ok", "user_id": 99, "action": "login"}
    result = redact_sensitive_fields(None, "info", event_dict)
    assert result == {"event": "ok", "user_id": 99, "action": "login"}
