"""Tenant service layer."""


def normalize_tenant_slug(slug: str) -> str:
    return slug.strip().lower().replace(" ", "-")
