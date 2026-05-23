"""
Integration tests: registration + password-reset HTTP endpoints.

SAAS-203 acceptance criteria:
  POST /api/v1/auth/register/
  POST /api/v1/auth/password/reset/
  POST /api/v1/auth/password/reset/confirm/
"""

import json
import re

import pytest
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

REGISTER_URL = "/api/v1/auth/register/"
RESET_URL = "/api/v1/auth/password/reset/"
CONFIRM_URL = "/api/v1/auth/password/reset/confirm/"
TOKEN_URL = "/api/v1/auth/token/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def can_login(client, username, password):
    resp = post_json(client, TOKEN_URL, {"username": username, "password": password})
    return resp.status_code == 200


def _uid(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def _token(user):
    return default_token_generator.make_token(user)


# ---------------------------------------------------------------------------
# Shared fixture: locmem email backend
# ---------------------------------------------------------------------------


@pytest.fixture
def locmem_email(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRegistration:
    def test_register_creates_user_returns_201(self, api_client):
        resp = post_json(
            api_client,
            REGISTER_URL,
            {"email": "newuser@example.com", "username": "newuser", "password": "StrongPass1!"},
        )
        assert resp.status_code == 201, resp.json()
        data = resp.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "password" not in data

    def test_registered_user_can_login(self, api_client):
        post_json(
            api_client,
            REGISTER_URL,
            {"email": "logintest@example.com", "username": "logintest", "password": "StrongPass1!"},
        )
        assert can_login(api_client, "logintest", "StrongPass1!")

    def test_duplicate_username_returns_409(self, api_client, db):
        User.objects.create_user(username="taken", email="taken@example.com", password="Pass123!")
        resp = post_json(
            api_client,
            REGISTER_URL,
            {"email": "other@example.com", "username": "taken", "password": "StrongPass1!"},
        )
        assert resp.status_code == 409

    def test_duplicate_email_returns_409(self, api_client, db):
        User.objects.create_user(username="orig", email="dup@example.com", password="Pass123!")
        resp = post_json(
            api_client,
            REGISTER_URL,
            {"email": "dup@example.com", "username": "other", "password": "StrongPass1!"},
        )
        assert resp.status_code == 409

    def test_weak_password_returns_400(self, api_client):
        resp = post_json(
            api_client,
            REGISTER_URL,
            {"email": "weak@example.com", "username": "weakuser", "password": "123"},
        )
        assert resp.status_code == 400

    def test_missing_fields_returns_400(self, api_client):
        resp = post_json(api_client, REGISTER_URL, {"username": "incomplete"})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Password reset — request
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPasswordResetRequest:
    @pytest.fixture(autouse=True)
    def _locmem(self, locmem_email):
        pass

    @pytest.fixture
    def ada(self, db):
        return User.objects.create_user(
            username="ada", email="ada@example.com", password="Pass123!"
        )

    def test_known_email_returns_200(self, api_client, ada):
        resp = post_json(api_client, RESET_URL, {"email": ada.email})
        assert resp.status_code == 200

    def test_unknown_email_also_returns_200(self, api_client, db):
        """Never reveal whether an email exists."""
        resp = post_json(api_client, RESET_URL, {"email": "ghost@nowhere.invalid"})
        assert resp.status_code == 200

    def test_known_email_triggers_mail(self, api_client, ada):
        post_json(api_client, RESET_URL, {"email": ada.email})
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [ada.email]

    def test_unknown_email_sends_no_mail(self, api_client, db):
        post_json(api_client, RESET_URL, {"email": "ghost@nowhere.invalid"})
        assert len(mail.outbox) == 0


# ---------------------------------------------------------------------------
# Password reset — confirm
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPasswordResetConfirm:
    @pytest.fixture(autouse=True)
    def _locmem(self, locmem_email):
        pass

    @pytest.fixture
    def carol(self, db):
        return User.objects.create_user(
            username="carol", email="carol@example.com", password="OldPass123!"
        )

    def test_valid_token_resets_password(self, api_client, carol):
        """Core AC: valid uid+token successfully changes the password."""
        resp = post_json(
            api_client,
            CONFIRM_URL,
            {"uid": _uid(carol), "token": _token(carol), "new_password": "BrandNewPass1!"},
        )
        assert resp.status_code == 200, resp.json()
        assert "reset successfully" in resp.json()["detail"]

    def test_new_password_accepted_for_login(self, api_client, carol):
        post_json(
            api_client,
            CONFIRM_URL,
            {"uid": _uid(carol), "token": _token(carol), "new_password": "BrandNewPass1!"},
        )
        assert can_login(api_client, "carol", "BrandNewPass1!")

    def test_old_password_rejected_after_reset(self, api_client, carol):
        post_json(
            api_client,
            CONFIRM_URL,
            {"uid": _uid(carol), "token": _token(carol), "new_password": "BrandNewPass1!"},
        )
        assert not can_login(api_client, "carol", "OldPass123!")

    def test_invalid_token_returns_400(self, api_client, carol):
        resp = post_json(
            api_client,
            CONFIRM_URL,
            {"uid": _uid(carol), "token": "wrong-token", "new_password": "BrandNewPass1!"},
        )
        assert resp.status_code == 400

    def test_token_reuse_returns_400(self, api_client, carol):
        uid, token = _uid(carol), _token(carol)
        post_json(
            api_client, CONFIRM_URL, {"uid": uid, "token": token, "new_password": "BrandNewPass1!"}
        )
        resp = post_json(
            api_client, CONFIRM_URL, {"uid": uid, "token": token, "new_password": "AnotherPass1!"}
        )
        assert resp.status_code == 400

    def test_invalid_uid_returns_400(self, api_client, carol):
        resp = post_json(
            api_client,
            CONFIRM_URL,
            {
                "uid": "!!!notvalidbase64!!!",
                "token": _token(carol),
                "new_password": "BrandNewPass1!",
            },
        )
        assert resp.status_code == 400

    def test_full_flow_via_email_body(self, api_client, carol):
        """
        End-to-end: request reset → inspect email body → extract uid+token
        → POST confirm → login with new password.
        """
        post_json(api_client, RESET_URL, {"email": carol.email})
        assert len(mail.outbox) == 1

        body = mail.outbox[0].body
        uid_match = re.search(r'"uid":\s*"([^"]+)"', body)
        token_match = re.search(r'"token":\s*"([^"]+)"', body)
        assert uid_match, f"uid not found in email body:\n{body}"
        assert token_match, f"token not found in email body:\n{body}"

        resp = post_json(
            api_client,
            CONFIRM_URL,
            {
                "uid": uid_match.group(1),
                "token": token_match.group(1),
                "new_password": "EmailFlowPass1!",
            },
        )
        assert resp.status_code == 200, resp.json()
        assert can_login(api_client, "carol", "EmailFlowPass1!")
