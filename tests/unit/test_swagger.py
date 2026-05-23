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
# Schema content tests — verify key endpoints are present in the OpenAPI spec
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def schema(django_db_setup, client):  # noqa: ARG001
    """Fetch the OpenAPI YAML schema once for all content tests."""
    import yaml

    resp = client.get("/api/schema/?format=yaml")
    assert resp.status_code == 200
    return yaml.safe_load(resp.content)


@pytest.mark.django_db
class TestSchemaContent:
    """Verify that key API paths and components appear in the generated schema."""

    # -- Auth endpoints -------------------------------------------------------

    def test_schema_contains_token_obtain(self, api_client):
        resp = api_client.get("/api/schema/?format=json")
        import json

        schema = json.loads(resp.content)
        assert "/api/v1/auth/token/" in schema["paths"], "Login endpoint must be present in schema"

    def test_schema_contains_token_refresh(self, api_client):
        import json

        resp = api_client.get("/api/schema/?format=json")
        schema = json.loads(resp.content)
        assert "/api/v1/auth/token/refresh/" in schema["paths"], (
            "Token-refresh endpoint must be present in schema"
        )

    def test_schema_contains_token_blacklist(self, api_client):
        import json

        resp = api_client.get("/api/schema/?format=json")
        schema = json.loads(resp.content)
        assert "/api/v1/auth/token/blacklist/" in schema["paths"], (
            "Token-blacklist (logout) endpoint must be present in schema"
        )

    def test_schema_contains_register(self, api_client):
        import json

        resp = api_client.get("/api/schema/?format=json")
        schema = json.loads(resp.content)
        assert "/api/v1/auth/register/" in schema["paths"], (
            "Registration endpoint must be present in schema"
        )

    def test_schema_contains_password_reset(self, api_client):
        import json

        resp = api_client.get("/api/schema/?format=json")
        schema = json.loads(resp.content)
        assert "/api/v1/auth/password/reset/" in schema["paths"], (
            "Password-reset request endpoint must be present in schema"
        )

    def test_schema_contains_password_reset_confirm(self, api_client):
        import json

        resp = api_client.get("/api/schema/?format=json")
        schema = json.loads(resp.content)
        assert "/api/v1/auth/password/reset/confirm/" in schema["paths"], (
            "Password-reset confirm endpoint must be present in schema"
        )

    # -- Tenant / RBAC endpoints ----------------------------------------------

    def test_schema_contains_tenants(self, api_client):
        """Tenants endpoints, when present, must be under /api/v1/tenants/.

        NOTE: The tenants app currently exposes no routes (urlpatterns = []).
        This test will assert correctness once routes are added and will not
        fail while the app is still empty.
        """
        import json

        resp = api_client.get("/api/schema/?format=json")
        schema = json.loads(resp.content)
        # Any path that mentions "tenants" must be under the /api/v1/ prefix.
        wrong_prefix = [
            p for p in schema["paths"] if "tenants" in p and not p.startswith("/api/v1/tenants/")
        ]
        assert not wrong_prefix, f"Tenant paths under wrong prefix: {wrong_prefix}"

    def test_schema_contains_rbac(self, api_client):
        import json

        resp = api_client.get("/api/schema/?format=json")
        schema = json.loads(resp.content)
        rbac_paths = [p for p in schema["paths"] if p.startswith("/api/v1/rbac/")]
        assert rbac_paths, "At least one /api/v1/rbac/ path must appear in schema"

    # -- Security scheme ------------------------------------------------------

    def test_schema_has_bearer_security_scheme(self, api_client):
        import json

        resp = api_client.get("/api/schema/?format=json")
        schema = json.loads(resp.content)
        schemes = schema.get("components", {}).get("securitySchemes", {})
        assert "BearerAuth" in schemes, "BearerAuth security scheme must be declared in components"
        assert schemes["BearerAuth"]["scheme"] == "bearer"

    # -- Metadata -------------------------------------------------------------

    def test_schema_title_and_version(self, api_client):
        import json

        resp = api_client.get("/api/schema/?format=json")
        schema = json.loads(resp.content)
        info = schema.get("info", {})
        assert info.get("title") == "Django SaaS Kit API"
        assert info.get("version") == "1.0.0"

    # -- All paths are under /api/v1/ prefix ----------------------------------

    def test_all_paths_under_api_v1(self, api_client):
        """No endpoint should appear under a bare /api/ prefix."""
        import json

        resp = api_client.get("/api/schema/?format=json")
        schema = json.loads(resp.content)
        schema_paths = schema.get("paths", {})
        # Exclude the schema/docs/redoc meta-endpoints themselves
        # Only check paths that start with /api/ — non-versioned utility endpoints
        # (e.g. /health/) live outside /api/ by design and are excluded.
        api_paths = [
            p
            for p in schema_paths
            if p.startswith("/api/")
            and not p.startswith("/api/schema")
            and not p.startswith("/api/docs")
            and not p.startswith("/api/redoc")
        ]
        bad = [p for p in api_paths if not p.startswith("/api/v1/")]
        assert not bad, f"API paths not under /api/v1/: {bad}"
