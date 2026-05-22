"""User domain service layer."""


def get_display_name(user) -> str:
    full_name = user.get_full_name().strip()
    return full_name or getattr(user, "username", str(user))
