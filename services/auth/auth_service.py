"""Authentication use-cases — no HTTP dependencies."""

from django.contrib.auth.models import AbstractBaseUser


class AuthService:
    # TODO: Add your business logic here

    @staticmethod
    def is_authenticated(user: AbstractBaseUser | None) -> bool:
        return bool(user and user.is_authenticated)
