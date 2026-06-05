"""Unit tests for SocialAuthService OAuth token validation."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from services.auth.social_auth_service import SocialAuthService
from services.exceptions import ConflictServiceError, ValidationServiceError

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_authenticate_rejects_unsupported_provider():
    with pytest.raises(ValidationServiceError, match="Unsupported provider"):
        SocialAuthService.authenticate("twitter", "token")


def test_google_authenticate_creates_user(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "email": "new.google@example.com",
        "email_verified": True,
        "given_name": "New",
        "family_name": "User",
        "sub": "google-sub-1",
    }
    mock_response.raise_for_status = MagicMock()
    mocker.patch("services.auth.social_auth_service.requests.get", return_value=mock_response)

    user = SocialAuthService.authenticate("google", "valid-token")

    assert user.email == "new.google@example.com"
    assert user.check_password("") is False
    assert User.objects.filter(email="new.google@example.com").exists()


def test_google_authenticate_returns_existing_user(mocker):
    existing = User.objects.create_user(
        username="existing",
        email="existing@example.com",
        password="unused",
    )
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "email": "existing@example.com",
        "email_verified": True,
        "given_name": "Existing",
        "family_name": "User",
        "sub": "google-sub-2",
    }
    mock_response.raise_for_status = MagicMock()
    mocker.patch("services.auth.social_auth_service.requests.get", return_value=mock_response)

    user = SocialAuthService.authenticate("google", "valid-token")

    assert user.pk == existing.pk


def test_google_authenticate_rejects_unverified_email(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "email": "unverified@example.com",
        "email_verified": False,
        "sub": "google-sub-3",
    }
    mock_response.raise_for_status = MagicMock()
    mocker.patch("services.auth.social_auth_service.requests.get", return_value=mock_response)

    with pytest.raises(ValidationServiceError, match="not verified"):
        SocialAuthService.authenticate("google", "valid-token")


def test_github_authenticate_fetches_primary_email(mocker):
    user_response = MagicMock()
    user_response.json.return_value = {
        "id": 42,
        "login": "octocat",
        "name": "Octo Cat",
        "email": None,
    }
    user_response.raise_for_status = MagicMock()

    emails_response = MagicMock()
    emails_response.json.return_value = [
        {"email": "octo@example.com", "primary": True, "verified": True},
    ]
    emails_response.raise_for_status = MagicMock()

    mocker.patch(
        "services.auth.social_auth_service.requests.get",
        side_effect=[user_response, emails_response],
    )

    user = SocialAuthService.authenticate("github", "gho_token")

    assert user.email == "octo@example.com"
    assert user.first_name == "Octo"


def test_get_or_create_user_raises_conflict_on_integrity_error(mocker):
    from django.db import IntegrityError
    from services.auth.social_auth_service import SocialUserInfo

    info = SocialUserInfo(
        email="conflict@example.com",
        username="new_user",
        first_name="A",
        last_name="B",
        provider="google",
        provider_id="id-1",
    )
    mocker.patch.object(User, "save", side_effect=IntegrityError("duplicate key"))

    with pytest.raises(ConflictServiceError):
        SocialAuthService._get_or_create_user(info)
