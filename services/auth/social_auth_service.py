"""Social authentication service — validates OAuth tokens with Google / GitHub."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from services.exceptions import ConflictServiceError, ValidationServiceError

User = get_user_model()
log = logging.getLogger(__name__)

_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
_GITHUB_USER_URL = "https://api.github.com/user"
_GITHUB_EMAILS_URL = "https://api.github.com/user/emails"
_REQUEST_TIMEOUT = 10  # seconds


@dataclass(frozen=True)
class SocialUserInfo:
    email: str
    username: str
    first_name: str
    last_name: str
    provider: str
    provider_id: str


class SocialAuthService:
    """Validate a provider access token and return (or create) the matching User."""

    @staticmethod
    def authenticate(provider: str, access_token: str):
        """
        Validate *access_token* with *provider* and return the User.

        Raises:
            ValidationServiceError: token invalid / provider unsupported
            ConflictServiceError: email already registered via a different provider
        """
        provider = provider.lower()
        if provider == "google":
            info = SocialAuthService._fetch_google(access_token)
        elif provider == "github":
            info = SocialAuthService._fetch_github(access_token)
        else:
            raise ValidationServiceError(f"Unsupported provider: {provider!r}")

        return SocialAuthService._get_or_create_user(info)

    # ------------------------------------------------------------------
    # Provider-specific token introspection
    # ------------------------------------------------------------------

    @staticmethod
    def _fetch_google(access_token: str) -> SocialUserInfo:
        try:
            resp = requests.get(
                _GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            log.warning("social_auth.google_fetch_failed: %s", exc)
            raise ValidationServiceError("Google token validation failed.") from exc

        email = data.get("email", "").strip().lower()
        if not email:
            raise ValidationServiceError("Google did not return an email address.")
        if not data.get("email_verified"):
            raise ValidationServiceError("Google email is not verified.")

        given = data.get("given_name", "")
        family = data.get("family_name", "")
        sub = data.get("sub", "")
        username = SocialAuthService._make_username("google", email)

        return SocialUserInfo(
            email=email,
            username=username,
            first_name=given,
            last_name=family,
            provider="google",
            provider_id=sub,
        )

    @staticmethod
    def _fetch_github(access_token: str) -> SocialUserInfo:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }
        try:
            user_resp = requests.get(_GITHUB_USER_URL, headers=headers, timeout=_REQUEST_TIMEOUT)
            user_resp.raise_for_status()
            user_data = user_resp.json()

            # GitHub may not expose email in the user object — fetch separately.
            email = (user_data.get("email") or "").strip().lower()
            if not email:
                emails_resp = requests.get(
                    _GITHUB_EMAILS_URL, headers=headers, timeout=_REQUEST_TIMEOUT
                )
                emails_resp.raise_for_status()
                for entry in emails_resp.json():
                    if entry.get("primary") and entry.get("verified"):
                        email = entry["email"].strip().lower()
                        break
        except requests.RequestException as exc:
            log.warning("social_auth.github_fetch_failed: %s", exc)
            raise ValidationServiceError("GitHub token validation failed.") from exc

        if not email:
            raise ValidationServiceError("GitHub did not return a verified primary email.")

        login = user_data.get("login", "")
        name_parts = (user_data.get("name") or "").split(" ", 1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        username = SocialAuthService._make_username("github", login or email)

        return SocialUserInfo(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            provider="github",
            provider_id=str(user_data.get("id", "")),
        )

    # ------------------------------------------------------------------
    # User resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _get_or_create_user(info: SocialUserInfo):
        """Return existing user by email, or create a new one (unusable password)."""
        existing = User.objects.filter(email=info.email).first()
        if existing:
            return existing

        # New user — create with an unusable password (OAuth only)
        username = SocialAuthService._unique_username(info.username)
        try:
            with transaction.atomic():
                user = User(
                    username=username,
                    email=info.email,
                    first_name=info.first_name,
                    last_name=info.last_name,
                )
                user.set_unusable_password()
                user.save()
        except IntegrityError as exc:
            raise ConflictServiceError(
                "An account with those credentials already exists."
            ) from exc

        return user

    @staticmethod
    def _make_username(provider: str, base: str) -> str:
        """Derive a clean username from provider + base string."""
        import re

        clean = re.sub(r"[^\w]", "_", base).strip("_")[:30]
        return clean or f"{provider}_user"

    @staticmethod
    def _unique_username(base: str) -> str:
        """Append a counter suffix until the username is unique."""
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}_{counter}"
            counter += 1
        return username
