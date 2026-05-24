"""
Unit tests for PasswordResetService (service-layer only, no HTTP).

Email is captured via pytest-django's ``settings`` fixture, which overrides
EMAIL_BACKEND to locmem for the tests that need it.
"""

import pytest
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from django.core import mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from services.auth import PasswordResetService
from services.exceptions import ValidationServiceError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uid(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def _token(user):
    return default_token_generator.make_token(user)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="alice",
        email="alice@example.com",
        password="OldPass123!",
    )


@pytest.fixture
def locmem_email(settings):
    """Switch to in-memory email backend so outbox is available."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


# ---------------------------------------------------------------------------
# request_reset
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPasswordResetRequest:
    def test_sends_email_to_registered_address(self, user, locmem_email):
        PasswordResetService.request_reset(user.email)
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [user.email]

    def test_email_contains_uid_and_token(self, user, locmem_email):
        PasswordResetService.request_reset(user.email)
        body = mail.outbox[0].body
        assert _uid(user) in body, "Email body must contain the uid"
        assert "token" in body.lower(), "Email body must mention token"

    def test_unknown_email_sends_no_mail(self, db, locmem_email):
        """User-enumeration guard: unknown address → no email, no exception."""
        PasswordResetService.request_reset("ghost@nowhere.invalid")
        assert len(mail.outbox) == 0

    def test_email_lookup_is_case_insensitive(self, user, locmem_email):
        PasswordResetService.request_reset(user.email.upper())
        assert len(mail.outbox) == 1


# ---------------------------------------------------------------------------
# confirm_reset
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPasswordResetConfirm:
    def test_valid_token_sets_new_password(self, user):
        PasswordResetService.confirm_reset(_uid(user), _token(user), "NewSecurePass1!")
        user.refresh_from_db()
        assert user.check_password("NewSecurePass1!")

    def test_old_password_rejected_after_reset(self, user):
        PasswordResetService.confirm_reset(_uid(user), _token(user), "NewSecurePass1!")
        user.refresh_from_db()
        assert not user.check_password("OldPass123!")

    def test_token_invalidated_after_use(self, user):
        """
        Tokens are HMAC-signed over the hashed password.
        After set_password the hash changes → same token is rejected.
        """
        uid, token = _uid(user), _token(user)
        PasswordResetService.confirm_reset(uid, token, "NewSecurePass1!")
        with pytest.raises(ValidationServiceError, match="invalid or has already been used"):
            PasswordResetService.confirm_reset(uid, token, "AnotherPass1!")

    def test_invalid_token_raises(self, user):
        with pytest.raises(ValidationServiceError, match="invalid"):
            PasswordResetService.confirm_reset(_uid(user), "bad-token", "NewPass1!")

    def test_malformed_uid_raises(self, user):
        with pytest.raises(ValidationServiceError, match="Invalid"):
            PasswordResetService.confirm_reset("!!!notbase64!!!", _token(user), "NewPass1!")

    def test_nonexistent_user_uid_raises(self, db):
        fake_uid = urlsafe_base64_encode(force_bytes(99999999))
        with pytest.raises(ValidationServiceError, match="Invalid"):
            PasswordResetService.confirm_reset(fake_uid, "any-token", "NewPass1!")

    def test_weak_password_raises(self, user):
        token_gen = PasswordResetTokenGenerator()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_gen.make_token(user)
        with pytest.raises(ValidationServiceError, match="too short|too common|entirely numeric|similar"):
            PasswordResetService.confirm_reset(uid, token, "abc")
