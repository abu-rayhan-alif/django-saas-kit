import json

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


# ---------------------------------------------------------------------------
# Schema content tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSchemaContent:
    """Verify key API paths and components appear in the generated schema."""

    def _schema(self, api_client):
        resp = api_client.get("/api/schema/?format=json")
        assert resp.status_code == 200
        return json.loads(resp.content)

    def test_schema_contains_token_obtain(self, api_client):
        assert "/api/v1/auth/token/" in self._schema(api_client)["paths"]

    def test_schema_contains_token_refresh(self, api_client):
        assert "/api/v1/auth/token/refresh/" in self._schema(api_client)["paths"]

    def test_schema_contains_token_blacklist(self, api_client):
        assert "/api/v1/auth/token/blacklist/" in self._schema(api_client)["paths"]

    def test_schema_contains_register(self, api_client):
        assert "/api/v1/auth/register/" in self._schema(api_client)["paths"]

    def test_schema_contains_password_reset(self, api_client):
        assert "/api/v1/auth/password/reset/" in self._schema(api_client)["paths"]

    def test_schema_contains_password_reset_confirm(self, api_client):
        assert "/api/v1/auth/password/reset/confirm/" in self._schema(api_client)["paths"]

    def test_schema_contains_rbac(self, api_client):
        schema = self._schema(api_client)
        rbac_paths = [p for p in schema["paths"] if p.startswith("/api/v1/rbac/")]
        assert rbac_paths, "At least one /api/v1/rbac/ path must appear in schema"

    def test_schema_contains_tenants(self, api_client):
        """Tenant paths, when present, must be under /api/v1/tenants/."""
        schema = self._schema(api_client)
        wrong_prefix = [
            p for p in schema["paths"] if "tenants" in p and not p.startswith("/api/v1/tenants/")
        ]
        assert not wrong_prefix, f"Tenant paths under wrong prefix: {wrong_prefix}"

    def test_schema_has_bearer_security_scheme(self, api_client):
        schema = self._schema(api_client)
        schemes = schema.get("components", {}).get("securitySchemes", {})
        assert "BearerAuth" in schemes
        assert schemes["BearerAuth"]["scheme"] == "bearer"

    def test_schema_title_and_version(self, api_client):
        info = self._schema(api_client).get("info", {})
        assert info.get("title") == "Django SaaS Kit API"
        assert info.get("version") == "1.0.0"

    def test_all_api_paths_under_v1(self, api_client):
        """No /api/ path (excluding schema/docs/redoc) should be outside /api/v1/."""
        schema = self._schema(api_client)
        api_paths = [
            p
            for p in schema.get("paths", {})
            if p.startswith("/api/")
            and not p.startswith("/api/schema")
            and not p.startswith("/api/docs")
            and not p.startswith("/api/redoc")
        ]
        bad = [p for p in api_paths if not p.startswith("/api/v1/")]
        assert not bad, f"API paths not under /api/v1/: {bad}"
