import pytest


@pytest.mark.django_db
def test_health_endpoint_returns_ok(api_client, settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
    response = api_client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": "ok", "redis": "ok"},
    }


@pytest.mark.django_db
def test_health_endpoint_degraded_when_redis_fails(api_client, mocker):
    mocker.patch("apps.common.health_checks.check_redis", return_value="error")
    response = api_client.get("/health/")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["redis"] == "error"
    assert body["checks"]["database"] == "ok"
