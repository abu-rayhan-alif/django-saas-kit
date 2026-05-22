import pytest


@pytest.mark.django_db
def test_openapi_schema_is_available(api_client):
    response = api_client.get("/api/schema/")
    assert response.status_code == 200
    assert "application/vnd.oai.openapi" in response["Content-Type"]


def test_swagger_ui_is_available(api_client):
    response = api_client.get("/api/docs/")
    assert response.status_code == 200


def test_redoc_is_available(api_client):
    response = api_client.get("/api/redoc/")
    assert response.status_code == 200
