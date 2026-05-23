"""Tenant use-cases — no HTTP dependencies."""

import re

from services.exceptions import ValidationServiceError

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class TenantService:
    # TODO: Add your business logic here

    @staticmethod
    def normalize_slug(slug: str) -> str:
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
