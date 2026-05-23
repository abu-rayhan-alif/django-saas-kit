import pytest
from services.exceptions import ValidationServiceError
from services.tenants import TenantService


def test_normalize_slug():
    assert TenantService.normalize_slug("  My Tenant  ") == "my-tenant"


def test_validate_slug_rejects_invalid():
    with pytest.raises(ValidationServiceError):
        TenantService.validate_slug("invalid slug!")
