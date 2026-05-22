from unittest.mock import Mock

from services.auth_service import is_authenticated_request
from services.tenant_service import normalize_tenant_slug
from services.user_service import get_display_name


def test_normalize_tenant_slug():
    assert normalize_tenant_slug("  My Tenant  ") == "my-tenant"


def test_get_display_name_prefers_full_name():
    user = Mock(get_full_name=Mock(return_value="Jane Doe"), username="jane")
    assert get_display_name(user) == "Jane Doe"


def test_get_display_name_falls_back_to_username():
    user = Mock(get_full_name=Mock(return_value=""), username="jane")
    assert get_display_name(user) == "jane"


def test_is_authenticated_request():
    user = Mock(is_authenticated=True)
    assert is_authenticated_request(user) is True
    assert is_authenticated_request(None) is False
