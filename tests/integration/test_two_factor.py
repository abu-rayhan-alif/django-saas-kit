"""Integration tests for TOTP two-factor authentication."""

from __future__ import annotations

import json

import pyotp
import pytest
from apps.authentication.models import UserTOTP
from django.contrib.auth import get_user_model

SETUP_URL = "/api/v1/auth/2fa/setup/"
ENABLE_URL = "/api/v1/auth/2fa/enable/"
TOKEN_URL = "/api/v1/auth/token/"

User = get_user_model()


def _post_json(client, url: str, payload: dict, headers: dict | None = None):
    kwargs = {"content_type": "application/json"}
    if headers:
        kwargs.update(headers)
    return client.post(url, data=json.dumps(payload), **kwargs)


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
        username="twofauser",
        password="StrongPass123!",
        email="twofa@example.com",
    )


@pytest.mark.django_db
def test_2fa_setup_returns_secret_and_qr(api_client, user):
    headers = _auth_headers(api_client, user)
    response = api_client.get(SETUP_URL, **headers)

    assert response.status_code == 200
    data = response.json()
    assert "secret" in data
    assert "provisioning_uri" in data
    assert "<svg" in data["qr_svg"]
    assert UserTOTP.objects.filter(user=user, is_enabled=False).exists()


@pytest.mark.django_db
def test_2fa_enable_verifies_totp_code(api_client, user):
    headers = _auth_headers(api_client, user)
    setup = api_client.get(SETUP_URL, **headers)
    secret = setup.json()["secret"]
    code = pyotp.TOTP(secret).now()

    response = _post_json(api_client, ENABLE_URL, {"code": code}, headers)

    assert response.status_code == 200
    assert "backup_codes" in response.json()
    totp_obj = UserTOTP.objects.get(user=user)
    assert totp_obj.is_enabled is True
