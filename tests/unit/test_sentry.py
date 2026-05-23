"""SAAS-603 — Sentry integration."""

from __future__ import annotations

from apps.common.exceptions import saas_exception_handler
from apps.common.sentry import init_sentry


def test_init_sentry_skips_without_dsn(monkeypatch, mocker):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    mock_init = mocker.patch("sentry_sdk.init")
    assert init_sentry() is False
    mock_init.assert_not_called()


def test_init_sentry_skips_empty_dsn(monkeypatch, mocker):
    monkeypatch.setenv("SENTRY_DSN", "   ")
    mock_init = mocker.patch("sentry_sdk.init")
    assert init_sentry() is False
    mock_init.assert_not_called()


def test_init_sentry_configures_with_dsn(monkeypatch, mocker):
    monkeypatch.setenv("SENTRY_DSN", "https://key@o0.ingest.sentry.io/1")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "staging")
    monkeypatch.setenv("SENTRY_RELEASE", "django-saas-kit@0.1.0")
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.25")
    mock_init = mocker.patch("sentry_sdk.init")

    assert init_sentry() is True
    mock_init.assert_called_once()
    kwargs = mock_init.call_args.kwargs
    assert kwargs["dsn"] == "https://key@o0.ingest.sentry.io/1"
    assert kwargs["environment"] == "staging"
    assert kwargs["release"] == "django-saas-kit@0.1.0"
    assert kwargs["traces_sample_rate"] == 0.25
    assert kwargs["send_default_pii"] is False


def test_saas_exception_handler_captures_unhandled(mocker):
    mock_capture = mocker.patch("sentry_sdk.capture_exception")
    mocker.patch("sentry_sdk.is_initialized", return_value=True)
    mocker.patch(
        "apps.common.exceptions.drf_exception_handler",
        return_value=None,
    )

    exc = RuntimeError("boom")
    response = saas_exception_handler(exc, {"request": mocker.Mock()})

    assert response is not None
    assert response.status_code == 500
    mock_capture.assert_called_once_with(exc)


def test_saas_exception_handler_skips_capture_when_sentry_off(mocker):
    mock_capture = mocker.patch("sentry_sdk.capture_exception")
    mocker.patch("sentry_sdk.is_initialized", return_value=False)
    mocker.patch(
        "apps.common.exceptions.drf_exception_handler",
        return_value=None,
    )

    saas_exception_handler(RuntimeError("boom"), {"request": mocker.Mock()})
    mock_capture.assert_not_called()
