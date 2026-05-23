"""
Unit tests for the unified error envelope (SAAS-302).

Covers:
  - saas_exception_handler() shapes for 400, 401, 403, 404, 500
  - All responses carry {error, message, details} keys
  - Integration: hitting real endpoints returns the correct shape
"""

import json

import pytest
from apps.common.exceptions import saas_exception_handler
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENVELOPE_KEYS = {"error", "message", "details"}

TOKEN_URL = "/api/v1/auth/token/"


def _post_json(client, url: str, payload: dict):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def _auth_headers(token: str) -> dict:
    """Return Django test-client keyword args that set the Bearer token."""
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def _assert_envelope(data: dict) -> None:
    """Assert the response body matches the unified error envelope."""
    assert _ENVELOPE_KEYS == set(data.keys()), (
        f"Expected keys {_ENVELOPE_KEYS}, got {set(data.keys())}"
    )
    assert isinstance(data["error"], str) and data["error"]
    assert isinstance(data["message"], str) and data["message"]
    assert isinstance(data["details"], dict)


# ---------------------------------------------------------------------------
# Unit tests: saas_exception_handler() — no HTTP layer required
# ---------------------------------------------------------------------------


class TestExceptionHandlerUnit:
    """Direct tests of saas_exception_handler without Django test client."""

    _ctx: dict = {}  # empty context is fine for unit tests

    def test_validation_error_shape(self):
        exc = ValidationError({"email": ["This field is required."]})
        response = saas_exception_handler(exc, self._ctx)

        assert response is not None
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        _assert_envelope(response.data)
        assert response.data["error"] == "invalid"
        assert response.data["details"] == {"email": ["This field is required."]}

    def test_not_authenticated_shape(self):
        exc = NotAuthenticated()
        response = saas_exception_handler(exc, self._ctx)

        assert response is not None
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        _assert_envelope(response.data)
        assert response.data["error"] == "not_authenticated"

    def test_authentication_failed_shape(self):
        exc = AuthenticationFailed()
        response = saas_exception_handler(exc, self._ctx)

        assert response is not None
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        _assert_envelope(response.data)
        assert response.data["error"] == "authentication_failed"

    def test_permission_denied_shape(self):
        exc = PermissionDenied()
        response = saas_exception_handler(exc, self._ctx)

        assert response is not None
        assert response.status_code == status.HTTP_403_FORBIDDEN
        _assert_envelope(response.data)
        assert response.data["error"] == "permission_denied"

    def test_not_found_shape(self):
        exc = NotFound()
        response = saas_exception_handler(exc, self._ctx)

        assert response is not None
        assert response.status_code == status.HTTP_404_NOT_FOUND
        _assert_envelope(response.data)
        assert response.data["error"] == "not_found"

    def test_unhandled_exception_returns_500(self):
        exc = RuntimeError("something went very wrong")
        response = saas_exception_handler(exc, self._ctx)

        assert response is not None
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        _assert_envelope(response.data)
        assert response.data["error"] == "server_error"

    def test_validation_error_list_normalised_to_dict(self):
        """Non-field ValidationError (list detail) must still return details as dict."""
        exc = ValidationError(["Non-field error."])
        response = saas_exception_handler(exc, self._ctx)

        assert response is not None
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        _assert_envelope(response.data)
        # List is wrapped under non_field_errors key
        assert response.data["details"] == {"non_field_errors": ["Non-field error."]}


# ---------------------------------------------------------------------------
# Integration tests: real HTTP responses carry the unified envelope
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestErrorFormatIntegration:
    """Hit real endpoints and verify the error envelope on the wire."""

    def test_invalid_login_returns_envelope(self, api_client):
        """401 on bad credentials must use the unified shape."""
        resp = _post_json(
            api_client,
            TOKEN_URL,
            {"username": "nobody", "password": "wrong"},
        )
        assert resp.status_code == 401
        data = resp.json()
        _assert_envelope(data)

    def test_validation_error_on_register_returns_envelope(self, api_client):
        """400 on malformed registration payload must use the unified shape."""
        resp = _post_json(
            api_client,
            "/api/v1/auth/register/",
            {"username": "x"},  # missing required email + password
        )
        assert resp.status_code == 400
        data = resp.json()
        _assert_envelope(data)
        assert data["error"] == "invalid"
        # Details should list the offending fields
        assert "email" in data["details"] or "password" in data["details"]

    def test_unauthenticated_request_returns_envelope(self, api_client):
        """401 when no token is provided must use the unified shape."""
        resp = api_client.get("/api/v1/users/list/")
        assert resp.status_code == 401
        data = resp.json()
        _assert_envelope(data)

    def test_non_admin_forbidden_returns_envelope(self, api_client, db):
        """403 when a regular user hits an admin-only endpoint."""
        from django.contrib.auth.models import User

        User.objects.create_user(username="plain", password="Pass1234!")
        login = _post_json(
            api_client,
            TOKEN_URL,
            {"username": "plain", "password": "Pass1234!"},
        )
        access = login.json()["access"]

        resp = api_client.get("/api/v1/users/list/", **_auth_headers(access))
        assert resp.status_code == 403
        data = resp.json()
        _assert_envelope(data)
        assert data["error"] == "permission_denied"

    def test_404_non_existent_url_returns_envelope(self, api_client):
        """404 on a completely unknown URL must use the unified shape."""
        resp = api_client.get("/api/v1/does-not-exist-xyz/")
        assert resp.status_code == 404
        data = resp.json()
        _assert_envelope(data)
        assert data["error"] == "not_found"
