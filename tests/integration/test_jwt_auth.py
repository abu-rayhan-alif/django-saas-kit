"""
Integration test: JWT login → refresh → logout (blacklist) flow.

Covers SAAS-201 acceptance criteria:
  - POST /api/v1/auth/token/          — login, returns access + refresh
  - POST /api/v1/auth/token/refresh/  — rotates refresh, returns new tokens
  - POST /api/v1/auth/token/blacklist/ — blacklists refresh (logout)
  - Blacklisted refresh token is rejected on re-use
"""

import json

import pytest
from django.contrib.auth.models import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TOKEN_URL = "/api/v1/auth/token/"
REFRESH_URL = "/api/v1/auth/token/refresh/"
BLACKLIST_URL = "/api/v1/auth/token/blacklist/"


def _post_json(client, url: str, payload: dict):
    return client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    """Create a plain active user for auth tests."""
    return User.objects.create_user(
        username="testuser",
        password="StrongPass123!",
        email="testuser@example.com",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestJWTAuthFlow:
    """Full login → refresh → logout integration flow."""

    def test_login_returns_access_and_refresh_tokens(self, api_client, user):
        response = _post_json(
            api_client,
            TOKEN_URL,
            {"username": "testuser", "password": "StrongPass123!"},
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "access" in data, "login response must include access token"
        assert "refresh" in data, "login response must include refresh token"

    def test_refresh_rotates_token(self, api_client, user):
        # Step 1 — login
        login_resp = _post_json(
            api_client,
            TOKEN_URL,
            {"username": "testuser", "password": "StrongPass123!"},
        )
        assert login_resp.status_code == 200
        original_refresh = login_resp.json()["refresh"]

        # Step 2 — refresh
        refresh_resp = _post_json(
            api_client,
            REFRESH_URL,
            {"refresh": original_refresh},
        )
        assert refresh_resp.status_code == 200, refresh_resp.json()
        data = refresh_resp.json()
        assert "access" in data, "refresh response must include new access token"
        assert "refresh" in data, "refresh response must include new refresh token (rotation)"
        # Rotated token must differ from the original
        assert data["refresh"] != original_refresh, "rotated refresh token must be a new token"

    def test_logout_blacklists_refresh_token(self, api_client, user):
        # Step 1 — login
        login_resp = _post_json(
            api_client,
            TOKEN_URL,
            {"username": "testuser", "password": "StrongPass123!"},
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh"]

        # Step 2 — logout (blacklist)
        logout_resp = _post_json(
            api_client,
            BLACKLIST_URL,
            {"refresh": refresh_token},
        )
        assert logout_resp.status_code == 200, logout_resp.json()

    def test_blacklisted_token_is_rejected(self, api_client, user):
        # Step 1 — login
        login_resp = _post_json(
            api_client,
            TOKEN_URL,
            {"username": "testuser", "password": "StrongPass123!"},
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh"]

        # Step 2 — logout
        logout_resp = _post_json(
            api_client,
            BLACKLIST_URL,
            {"refresh": refresh_token},
        )
        assert logout_resp.status_code == 200

        # Step 3 — attempt to reuse the blacklisted refresh token
        reuse_resp = _post_json(
            api_client,
            REFRESH_URL,
            {"refresh": refresh_token},
        )
        assert reuse_resp.status_code == 401, (
            "blacklisted refresh token must be rejected with 401, "
            f"got {reuse_resp.status_code}: {reuse_resp.json()}"
        )

    def test_full_login_refresh_logout_flow(self, api_client, user):
        """End-to-end: login → refresh with original → logout rotated token → verify rejection."""
        # Login
        login_resp = _post_json(
            api_client,
            TOKEN_URL,
            {"username": "testuser", "password": "StrongPass123!"},
        )
        assert login_resp.status_code == 200
        original_refresh = login_resp.json()["refresh"]

        # Refresh — get a rotated token
        refresh_resp = _post_json(
            api_client,
            REFRESH_URL,
            {"refresh": original_refresh},
        )
        assert refresh_resp.status_code == 200
        rotated_refresh = refresh_resp.json()["refresh"]

        # Logout using the rotated token
        logout_resp = _post_json(
            api_client,
            BLACKLIST_URL,
            {"refresh": rotated_refresh},
        )
        assert logout_resp.status_code == 200

        # The rotated (now blacklisted) token must be rejected
        reuse_resp = _post_json(
            api_client,
            REFRESH_URL,
            {"refresh": rotated_refresh},
        )
        assert reuse_resp.status_code == 401

    def test_invalid_credentials_rejected(self, api_client, user):
        response = _post_json(
            api_client,
            TOKEN_URL,
            {"username": "testuser", "password": "WrongPassword!"},
        )
        assert response.status_code == 401

    def test_malformed_refresh_token_rejected(self, api_client):
        response = _post_json(
            api_client,
            REFRESH_URL,
            {"refresh": "not.a.valid.jwt"},
        )
        assert response.status_code == 401
