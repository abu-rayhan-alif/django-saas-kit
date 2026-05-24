"""Tenant use-cases — no HTTP dependencies."""

from __future__ import annotations

import re
from dataclasses import dataclass

from django.db import transaction

from services.exceptions import ConflictServiceError, ValidationServiceError

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class CreateTenantResult:
    tenant: object
    domain: object


class TenantService:

    @staticmethod
    def normalize_slug(slug: str) -> str:
        """Lowercase, strip whitespace, replace spaces with hyphens."""
        normalized = slug.strip().lower().replace(" ", "-")
        if not normalized:
            raise ValidationServiceError("Tenant slug cannot be empty.")
        return normalized

    @staticmethod
    def validate_slug(slug: str) -> str:
        normalized = TenantService.normalize_slug(slug)
        if not _SLUG_PATTERN.match(normalized):
            raise ValidationServiceError(
                "Slug may only contain lowercase letters, numbers, and hyphens."
            )
        return normalized

    @staticmethod
    def create_tenant(
        name: str,
        schema_name: str,
        domain: str,
        *,
        is_primary: bool = True,
    ) -> CreateTenantResult:
        """
        Create a Tenant and its primary Domain atomically.

        Parameters
        ----------
        name:        Human-readable display name (e.g. "Acme Corp").
        schema_name: URL-safe identifier used for subdomain routing
                     (e.g. "acme" → ``acme.localhost``).  Also used as
                     the ``slug`` for API paths.
        domain:      Full hostname string to register (e.g. "acme.localhost").
        is_primary:  Mark this Domain as the primary entry point.

        Raises
        ------
        ValidationServiceError  — invalid schema_name format.
        ConflictServiceError    — schema_name or domain already taken.
        """
        from apps.tenants.models import Domain, Tenant  # noqa: PLC0415

        schema_name = TenantService.validate_slug(schema_name)
        domain = domain.strip().lower()

        if not domain:
            raise ValidationServiceError("Domain cannot be empty.")

        if Tenant.objects.filter(schema_name=schema_name).exists():
            raise ConflictServiceError(f"schema_name '{schema_name}' is already taken.")
        if Domain.objects.filter(domain=domain).exists():
            raise ConflictServiceError(f"Domain '{domain}' is already registered.")

        with transaction.atomic():
            tenant = Tenant.objects.create(
                name=name.strip(),
                slug=schema_name,
                schema_name=schema_name,
            )
            domain_obj = Domain.objects.create(
                tenant=tenant,
                domain=domain,
                is_primary=is_primary,
            )

        return CreateTenantResult(tenant=tenant, domain=domain_obj)
