"""User use-cases — no HTTP or DRF dependencies."""

from dataclasses import dataclass

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


class UserService:
    """User registration and profile use-cases."""

    # TODO: Add your business logic here

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

        user_id = user.pk
        transaction.on_commit(lambda uid=user_id: _enqueue_welcome_email(uid))

        return user

    @staticmethod
    def get_display_name(user: AbstractUser) -> str:
        full_name = user.get_full_name().strip()
        return full_name or user.username


def _enqueue_welcome_email(user_id: int) -> None:
    from apps.users.tasks import send_welcome_email

    send_welcome_email.delay(user_id)
