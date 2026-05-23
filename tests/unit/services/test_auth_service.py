from unittest.mock import Mock

from services.auth import AuthService


def test_is_authenticated():
    user = Mock(is_authenticated=True)
    assert AuthService.is_authenticated(user) is True
    assert AuthService.is_authenticated(None) is False
