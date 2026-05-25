"""
Suppress the test-tenant auto-assignment signal for all service unit tests.

Service unit tests create users with explicit role setups; the global
post_save signal in the root conftest would add extra test-tenant roles that
break role-count assertions (e.g. GDPR tests, seed-service idempotency tests).
"""

import pytest
from tests import suppress_auto_tenant as _suppress


@pytest.fixture(autouse=True)
def _no_auto_tenant():
    _suppress.active = True
    yield
    _suppress.active = False
