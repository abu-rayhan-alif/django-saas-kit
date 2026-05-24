"""
Unit / integration tests for StandardPagination (SAAS-302).

Covers:
  - Paginated list responses carry {count, next, previous, results}
  - page_size query parameter is respected (up to max_page_size=100)
  - page_size_query_param name is "page_size"
  - Filtering via UserFilter works end-to-end
"""

import json

import pytest
from django.contrib.auth.models import User

TOKEN_URL = "/api/v1/auth/token/"
USER_LIST_URL = "/api/v1/users/list/"


def _post_json(client, url: str, payload: dict):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def _auth_headers(token: str) -> dict:
    """Return Django test-client keyword args that set the Bearer token."""
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def _get_admin_token(client) -> tuple[str, User]:
    admin = User.objects.create_superuser(
        username="admin", password="Admin1234!", email="admin@example.com"
    )
    resp = _post_json(client, TOKEN_URL, {"username": "admin", "password": "Admin1234!"})
    assert resp.status_code == 200, resp.json()
    return resp.json()["access"], admin


@pytest.mark.django_db
class TestPagination:
    """Verify StandardPagination response envelope on the user list endpoint."""

    def test_paginated_response_has_required_keys(self, api_client):
        token, _ = _get_admin_token(api_client)

        resp = api_client.get(USER_LIST_URL, **_auth_headers(token))
        assert resp.status_code == 200, resp.json()
        data = resp.json()

        assert set(data.keys()) >= {
            "count",
            "next",
            "previous",
            "results",
        }, f"Paginated response must have count/next/previous/results, got: {list(data.keys())}"
        assert isinstance(data["results"], list)
        assert isinstance(data["count"], int)

    def test_page_size_query_param_respected(self, api_client):
        """?page_size=1 must return only 1 result."""
        for i in range(3):
            User.objects.create_user(username=f"user{i}", password="Pass123!")

        token, _ = _get_admin_token(api_client)

        resp = api_client.get(f"{USER_LIST_URL}?page_size=1", **_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 1
        assert data["next"] is not None  # there are more pages

    def test_default_page_size_is_20(self):
        from apps.common.pagination import StandardPagination

        assert StandardPagination.page_size == 20

    def test_max_page_size_is_100(self):
        from apps.common.pagination import StandardPagination

        assert StandardPagination.max_page_size == 100

    def test_page_size_query_param_name(self):
        from apps.common.pagination import StandardPagination

        assert StandardPagination.page_size_query_param == "page_size"


@pytest.mark.django_db
class TestFiltering:
    """Verify django-filter integration on the user list endpoint."""

    def test_filter_by_is_active_true(self, api_client):
        User.objects.create_user(username="active_u", password="P!", is_active=True)
        User.objects.create_user(username="inactive_u", password="P!", is_active=False)

        token, _ = _get_admin_token(api_client)

        resp = api_client.get(f"{USER_LIST_URL}?is_active=true", **_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        usernames = [u["username"] for u in data["results"]]
        assert "active_u" in usernames
        assert "inactive_u" not in usernames

    def test_filter_by_is_active_false(self, api_client):
        User.objects.create_user(username="inactive2", password="P!", is_active=False)

        token, _ = _get_admin_token(api_client)

        resp = api_client.get(f"{USER_LIST_URL}?is_active=false", **_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        usernames = [u["username"] for u in data["results"]]
        assert "inactive2" in usernames
        assert "admin" not in usernames

    def test_search_by_username(self, api_client):
        User.objects.create_user(username="findme123", password="P!")

        token, _ = _get_admin_token(api_client)

        resp = api_client.get(f"{USER_LIST_URL}?search=findme123", **_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        usernames = [u["username"] for u in data["results"]]
        assert "findme123" in usernames

    def test_ordering_by_username_asc(self, api_client):
        User.objects.create_user(username="aaa_first", password="P!")
        User.objects.create_user(username="zzz_last", password="P!")

        token, _ = _get_admin_token(api_client)

        resp = api_client.get(f"{USER_LIST_URL}?ordering=username", **_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        usernames = [u["username"] for u in data["results"]]
        assert usernames == sorted(usernames)
