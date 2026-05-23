"""
Stable demo identifiers for ``seed_demo`` and Swagger examples.

Run ``python manage.py seed_demo`` after migrations to create these records.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

# Fixed UUIDs so OpenAPI examples match the database after seeding.
TENANT1_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
TENANT2_ID = uuid.UUID("00000000-0000-4000-8000-000000000002")

DEMO_ADMIN_EMAIL = "admin@tenant1.localhost"
DEMO_ADMIN_USERNAME = "admin@tenant1.localhost"
DEMO_ADMIN_PASSWORD = "password123"


@dataclass(frozen=True)
class DemoTenantSpec:
    id: uuid.UUID
    name: str
    slug: str


@dataclass(frozen=True)
class DemoAdminSpec:
    email: str
    username: str
    password: str
    first_name: str = "Demo"
    last_name: str = "Admin"
    role: str = "admin"


DEMO_TENANTS: tuple[DemoTenantSpec, ...] = (
    DemoTenantSpec(id=TENANT1_ID, name="Tenant One", slug="tenant1"),
    DemoTenantSpec(id=TENANT2_ID, name="Tenant Two", slug="tenant2"),
)

DEMO_ADMIN = DemoAdminSpec(
    email=DEMO_ADMIN_EMAIL,
    username=DEMO_ADMIN_USERNAME,
    password=DEMO_ADMIN_PASSWORD,
)
