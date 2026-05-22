"""Authentication service layer."""


def is_authenticated_request(user) -> bool:
    return bool(user and user.is_authenticated)
