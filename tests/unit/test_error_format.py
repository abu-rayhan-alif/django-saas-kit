"""
Unit tests for the unified error envelope (SAAS-302).
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
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def _assert_envelope(data: dict) -> None:
    assert _ENVELOPE_KEYS == set(data.keys()), (
        f"Expected keys {_ENVELOPE_KEYS}, got {set(data.keys())}"
    )
    assert isinstance(data["error"], str) and data["error"]
    assert isinstance(data["message"], str) and data["message"]
    assert isinstance(data["details"], dict)


# ---------------------------------------------------------------------------
# Unit tests — no HTTP layer
# ---------------------------------------------------------------------------


class TestExceptionHandlerUnit:
    _ctx: dict = {}

    def test_validation_error_shape(self):
        exc = ValidationError({"email": ["This field is required."]})
        resp = saas_exception_handler(exc, self._ctx)
        assert resp is not None
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        _assert_envelope(resp.data)
        assert resp.data["error"] == "invalid"
        assert resp.data["details"] == {"email": ["This field is required."]}

    def test_not_authenticated_shape(self):
        exc = NotAuthenticated()
        resp = saas_exception_handler(exc, self._ctx)
        assert resp is not None
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        _assert_envelope(resp.data)
        assert resp.data["error"] == "not_authenticated"

    def test_authentication_failed_shape(self):
        exc = AuthenticationFailed()
        resp = saas_exception_handler(exc, self._ctx)
        assert resp is not None
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        _assert_envelope(resp.data)
        assert resp.data["error"] == "authentication_failed"

    def test_permission_denied_shape(self):
        exc = PermissionDenied()
        resp = saas_exception_handler(exc, self._ctx)
        assert resp is not None
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        _assert_envelope(resp.data)
        assert resp.data["error"] == "permission_denied"

    def test_not_found_shape(self):
        exc = NotFound()
        resp = saas_exception_handler(exc, self._ctx)
        assert resp is not None
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        _assert_envelope(resp.data)
        assert resp.data["error"] == "not_found"

    def test_unhandled_exception_returns_500(self):
        exc = RuntimeError("boom")
        resp = saas_exception_handler(exc, self._ctx)
        assert resp is not None
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        _assert_envelope(resp.data)
        assert resp.data["error"] == "server_error"

    def test_validation_error_list_normalised_to_dict(self):
        exc = ValidationError(["Non-field error."])
        resp = saas_exception_handler(exc, self._ctx)
        assert resp is not None
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        _assert_envelope(resp.data)
        assert resp.data["details"] == {"non_field_errors": ["Non-field error."]}


# ---------------------------------------------------------------------------
# Integration tests — real HTTP responses
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestErrorFormatIntegration:
    def test_invalid_login_returns_envelope(self, api_client):
        resp = _post_json(api_client, TOKEN_URL, {"username": "nobody", "password": "wrong"})
        assert resp.status_code == 401
        _assert_envelope(resp.json())

    def test_validation_error_on_register_returns_envelope(self, api_client):
        resp = _post_json(api_client, "/api/v1/auth/register/", {"username": "x"})
        assert resp.status_code == 400
        data = resp.json()
        _assert_envelope(data)
        assert data["error"] == "invalid"
        assert "email" in data["details"] or "password" in data["details"]

    def test_unauthenticated_request_returns_envelope(self, api_client):
        resp = api_client.get("/api/v1/users/list/")
        assert resp.status_code == 401
        _assert_envelope(resp.json())

    def test_non_admin_forbidden_returns_envelope(self, api_client, db):
        from django.contrib.auth.models import User

        User.objects.create_user(username="plain", password="Pass1234!")
        login = _post_json(api_client, TOKEN_URL, {"username": "plain", "password": "Pass1234!"})
        access = login.json()["access"]
        resp = api_client.get("/api/v1/users/list/", **_auth_headers(access))
        assert resp.status_code == 403
        data = resp.json()
        _assert_envelope(data)
        assert data["error"] == "permission_denied"

    def test_404_non_existent_url_returns_envelope(self, api_client):
        resp = api_client.get("/api/v1/does-not-exist-xyz/")
        assert resp.status_code == 404
        data = resp.json()
        _assert_envelope(data)
        assert data["error"] == "not_found"
