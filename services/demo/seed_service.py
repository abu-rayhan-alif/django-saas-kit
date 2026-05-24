"""Demo tenant and user seeding — no HTTP dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from apps.rbac.models import RoleChoices
from apps.tenants.models import Domain, Tenant
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.db import transaction
from examples.demo_config import DEMO_ADMIN, DEMO_TENANTS

from services.rbac import RBACService

User = get_user_model()


@dataclass(frozen=True)
class DemoSeedResult:
    tenants: tuple[Tenant, ...]
    admin_user: AbstractUser


class DemoSeedService:
    """Idempotent demo data for local development and API exploration."""

    # TODO: Add your business logic here

    @staticmethod
    @transaction.atomic
    def seed() -> DemoSeedResult:
        tenants = tuple(DemoSeedService._ensure_tenants())
        admin_user = DemoSeedService._ensure_admin_user()
        tenant1 = next(t for t in tenants if t.slug == "tenant1")
        RBACService.assign_role(admin_user, tenant1, RoleChoices.ADMIN)
        return DemoSeedResult(tenants=tenants, admin_user=admin_user)

    @staticmethod
    def _ensure_tenants() -> list[Tenant]:
        tenants: list[Tenant] = []
        for spec in DEMO_TENANTS:
            tenant, _ = Tenant.objects.update_or_create(
                id=spec.id,
                defaults={
                    "name": spec.name,
                    "slug": spec.slug,
                    "schema_name": spec.slug,
                },
            )
            Domain.objects.update_or_create(
                tenant=tenant,
                domain=f"{spec.slug}.localhost",
                defaults={"is_primary": True},
            )
            tenants.append(tenant)
        return tenants

    @staticmethod
    def _ensure_admin_user() -> AbstractUser:
        user, _ = User.objects.get_or_create(
            username=DEMO_ADMIN.username,
            defaults={
                "email": DEMO_ADMIN.email,
                "first_name": DEMO_ADMIN.first_name,
                "last_name": DEMO_ADMIN.last_name,
            },
        )
        user.email = DEMO_ADMIN.email
        user.first_name = DEMO_ADMIN.first_name
        user.last_name = DEMO_ADMIN.last_name
        user.set_password(DEMO_ADMIN.password)
        user.save()
        return user
