"""Shared drf-spectacular examples for demo API calls."""

from drf_spectacular.utils import OpenApiExample

from examples.demo_config import DEMO_ADMIN, TENANT1_ID

DEMO_LOGIN_REQUEST = OpenApiExample(
    "Demo tenant admin login",
    description=(
        "Credentials created by ``python manage.py seed_demo``. "
        "JWT login uses **username**, not email."
    ),
    value={
        "username": DEMO_ADMIN.username,
        "password": DEMO_ADMIN.password,
    },
    request_only=True,
)

DEMO_RBAC_TENANT_ID = OpenApiExample(
    "Tenant One UUID (after seed_demo)",
    value=str(TENANT1_ID),
)
