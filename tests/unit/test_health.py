"""SAAS-602 — liveness (/health/) and readiness (/ready/) endpoints."""

import pytest


def test_health_endpoint_returns_ok_without_db(api_client):
    """Liveness: 200 even when dependencies are not probed."""
    response = api_client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_ready_endpoint_returns_ok(api_client, settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
    response = api_client.get("/ready/")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": "ok", "redis": "ok"},
    }


@pytest.mark.django_db
def test_ready_endpoint_not_ready_when_redis_fails(api_client, mocker):
    mocker.patch("apps.common.health_checks.check_redis", return_value="error")
    response = api_client.get("/ready/")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["redis"] == "error"
    assert body["checks"]["database"] == "ok"


@pytest.mark.django_db
def test_ready_endpoint_not_ready_when_database_fails(api_client, mocker):
    mocker.patch(
        "apps.common.health_checks.check_database",
        side_effect=Exception("db down"),
    )
    response = api_client.get("/ready/")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"] == "error"


def test_health_does_not_require_auth(api_client):
    response = api_client.get("/health/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_ready_does_not_require_auth(api_client, settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
    response = api_client.get("/ready/")
    assert response.status_code == 200
