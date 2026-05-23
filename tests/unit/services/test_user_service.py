import pytest
from django.contrib.auth import get_user_model
from services.exceptions import ConflictServiceError, ValidationServiceError
from services.users import CreateUserInput, UserService

User = get_user_model()


@pytest.mark.django_db
class TestUserServiceCreateUser:
    def test_create_user_success(self):
        user = UserService.create_user(
            CreateUserInput(
                email="alice@example.com",
                username="alice",
                password="SecurePass123!",
                first_name="Alice",
                last_name="Doe",
            )
        )

        assert user.pk is not None
        assert user.email == "alice@example.com"
        assert user.username == "alice"
        assert user.check_password("SecurePass123!")
        assert UserService.get_display_name(user) == "Alice Doe"

    def test_create_user_duplicate_username(self):
        UserService.create_user(
            CreateUserInput(
                email="first@example.com",
                username="alice",
                password="SecurePass123!",
            )
        )

        with pytest.raises(ConflictServiceError, match="(?i)username"):
            UserService.create_user(
                CreateUserInput(
                    email="second@example.com",
                    username="alice",
                    password="SecurePass123!",
                )
            )

    def test_create_user_duplicate_email(self):
        UserService.create_user(
            CreateUserInput(
                email="same@example.com",
                username="user_one",
                password="SecurePass123!",
            )
        )

        with pytest.raises(ConflictServiceError, match="(?i)email"):
            UserService.create_user(
                CreateUserInput(
                    email="same@example.com",
                    username="user_two",
                    password="SecurePass123!",
                )
            )

    def test_create_user_weak_password(self):
        with pytest.raises(ValidationServiceError, match="password"):
            UserService.create_user(
                CreateUserInput(
                    email="weak@example.com",
                    username="weakuser",
                    password="123",
                )
            )

    def test_create_user_invalid_email(self):
        with pytest.raises(ValidationServiceError, match="email"):
            UserService.create_user(
                CreateUserInput(
                    email="not-an-email",
                    username="bademail",
                    password="SecurePass123!",
                )
            )


def test_get_display_name_falls_back_to_username():
    user = User(username="jane", first_name="", last_name="")
    assert UserService.get_display_name(user) == "jane"
