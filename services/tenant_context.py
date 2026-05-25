"""Thread/coroutine-safe tenant context via contextvars.

Set once per request in TenantMiddleware; read anywhere — views, services,
Celery tasks — without passing tenant_id through every call.
"""

from __future__ import annotations

import contextvars
from uuid import UUID

_current_tenant_id: contextvars.ContextVar[UUID | None] = contextvars.ContextVar(
    "current_tenant_id", default=None
)


def set_tenant_id(tenant_id: UUID | None) -> None:
    _current_tenant_id.set(tenant_id)


def get_tenant_id() -> UUID | None:
    return _current_tenant_id.get()


def clear_tenant() -> None:
    _current_tenant_id.set(None)
