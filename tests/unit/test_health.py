import pytest


@pytest.mark.django_db
def test_health_endpoint_returns_ok(api_client):
    response = api_client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
