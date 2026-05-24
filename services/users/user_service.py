"""User use-cases -- no HTTP or DRF dependencies."""

from dataclasses import dataclass
from functools import partial
from typing import cast

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from services.exceptions import ConflictServiceError, ValidationServiceError

User = get_user_model()


@dataclass(frozen=True)
class CreateUserInput:
    email: str
    username: str
    password: str
    first_name: str = ""
    last_name: str = ""


def _enqueue_welcome_email(user_pk: int) -> None:
    """Called via transaction.on_commit -- imports lazily to avoid circular deps."""
    from apps.users.tasks import send_welcome_email  # noqa: PLC0415

    send_welcome_email.delay(user_pk)


class UserService:
    """User registration and profile use-cases."""

    @staticmethod
    def get_display_name(user: AbstractUser) -> str:
        """Return full name if set, else fall back to username."""
        full_name = f"{user.first_name} {user.last_name}".strip()
        return full_name if full_name else user.username

    @staticmethod
    def create_user(data: CreateUserInput) -> AbstractUser:
        """
        Create a new user with validated credentials.

        Raises:
            ValidationServiceError: invalid email, username, or password
            ConflictServiceError: username or email already taken
        """
        email = data.email.strip().lower()
        username = data.username.strip()

        if not email or "@" not in email:
            raise ValidationServiceError("A valid email address is required.")
        if not username:
            raise ValidationServiceError("Username is required.")
        if not data.password:
            raise ValidationServiceError("Password is required.")

        if User.objects.filter(username=username).exists():
            raise ConflictServiceError(f"Username '{username}' is already taken.")
        if User.objects.filter(email=email).exists():
            raise ConflictServiceError(f"Email '{email}' is already registered.")

        try:
            validate_password(data.password, user=User(username=username, email=email))
        except DjangoValidationError as exc:
            raise ValidationServiceError("; ".join(exc.messages)) from exc

        with transaction.atomic():
            user = User(
                username=username,
                email=email,
                first_name=data.first_name.strip(),
                last_name=data.last_name.strip(),
            )
            user.set_password(data.password)
            user.full_clean()
            user.save()
            # Register on_commit INSIDE the atomic block so it fires only after
            # the transaction successfully commits, never on rollback.
            transaction.on_commit(partial(_enqueue_welcome_email, cast(int, user.pk)))

        return user
