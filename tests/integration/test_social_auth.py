"""Integration tests for social OAuth login endpoint."""

from __future__ import annotations

import json

import pytest
from django.contrib.auth import get_user_model

SOCIAL_URL = "/api/v1/auth/social/"

User = get_user_model()


def _post_json(client, url: str, payload: dict):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


@pytest.mark.django_db
def test_social_auth_requires_provider_and_token(api_client):
    response = _post_json(api_client, SOCIAL_URL, {"provider": "google"})
    assert response.status_code == 400
    assert response.json()["field"] == "access_token"

    response = _post_json(api_client, SOCIAL_URL, {"access_token": "token"})
    assert response.status_code == 400
    assert response.json()["field"] == "provider"


@pytest.mark.django_db
def test_social_auth_returns_jwt_pair(mocker, api_client):
    user = User.objects.create_user(
        username="socialuser",
        email="social@example.com",
        password="unused",
    )
    mocker.patch(
        "apps.authentication.social_views.SocialAuthService.authenticate",
        return_value=user,
    )

    response = _post_json(
        api_client,
        SOCIAL_URL,
        {"provider": "google", "access_token": "valid-token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access" in data
    assert "refresh" in data
    assert data["created"] is False
