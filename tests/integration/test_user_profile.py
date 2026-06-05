"""Integration tests for user profile endpoints."""

from __future__ import annotations

import json

import pytest
from django.contrib.auth import get_user_model

ME_URL = "/api/v1/users/me/"
PROFILE_URL = "/api/v1/users/me/profile/"
TOKEN_URL = "/api/v1/auth/token/"

User = get_user_model()


def _post_json(client, url: str, payload: dict):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def _patch_json(client, url: str, payload: dict, headers: dict):
    return client.patch(
        url,
        data=json.dumps(payload),
        content_type="application/json",
        **headers,
    )


def _auth_headers(client, user, password: str = "StrongPass123!") -> dict:
    response = _post_json(
        client,
        TOKEN_URL,
        {"username": user.username, "password": password},
    )
    assert response.status_code == 200, response.json()
    access = response.json()["access"]
    return {"HTTP_AUTHORIZATION": f"Bearer {access}"}


@pytest.fixture()
def user(db):
    return User.objects.create_user(
        username="profileuser",
        password="StrongPass123!",
        email="profileuser@example.com",
        first_name="Profile",
        last_name="User",
    )


@pytest.mark.django_db
def test_me_endpoint_returns_user_and_profile(api_client, user):
    headers = _auth_headers(api_client, user)
    response = api_client.get(ME_URL, **headers)

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == user.username
    assert data["email"] == user.email
    assert "profile" in data
    assert data["profile"]["timezone"] == "UTC"


@pytest.mark.django_db
def test_profile_patch_updates_fields(api_client, user):
    headers = _auth_headers(api_client, user)
    response = _patch_json(
        api_client,
        PROFILE_URL,
        {"bio": "SaaS builder", "timezone": "UTC", "phone": "+15551234567"},
        headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["bio"] == "SaaS builder"
    assert data["phone"] == "+15551234567"


@pytest.mark.django_db
def test_profile_rejects_invalid_timezone(api_client, user):
    headers = _auth_headers(api_client, user)
    response = _patch_json(
        api_client,
        PROFILE_URL,
        {"timezone": "Not/A/Real/Zone"},
        headers,
    )

    assert response.status_code == 400
