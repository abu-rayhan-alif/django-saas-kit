"""
RBAC permission helpers.

Two mechanisms are provided — use whichever fits the view type:

* ``require_role(roles)``  — decorator for function-based or ``@method_decorator`` use
* ``HasRolePermission``    — DRF ``BasePermission`` for class-based views

Tenant resolution order
-----------------------
1. ``tenant_id`` URL kwarg (preferred — tenant is explicit in the URL)
2. ``X-Tenant-ID`` request header (fallback for headerless clients)
"""

from __future__ import annotations

import functools

from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from services.rbac import RBACService

from apps.tenants.models import Tenant

# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _resolve_tenant(request, kwargs: dict) -> Tenant | None:
    """
    Resolve a ``Tenant`` from URL kwargs or the ``X-Tenant-ID`` header.

    Returns ``None`` if the tenant cannot be found or the ID is malformed.
    """
    tenant_id = kwargs.get("tenant_id") or request.headers.get("X-Tenant-ID")
    if not tenant_id:
        return None
    try:
        return Tenant.objects.get(id=tenant_id)
    except (Tenant.DoesNotExist, ValueError):
        return None


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def require_role(roles: list[str]):
    """
    View decorator that enforces one of *roles* in the resolved tenant.

    Works for plain Django function-based views and can be applied to
    class-based views via ``@method_decorator(require_role([...]))``::

        @require_role(["admin", "owner"])
        def my_view(request, tenant_id):
            ...

    Raises :exc:`django.core.exceptions.PermissionDenied` (→ HTTP 403)
    when the requirement is not met.
    """

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            tenant = _resolve_tenant(request, kwargs)
            if tenant is None or not RBACService.has_role(request.user, tenant, roles):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# DRF permission class
# ---------------------------------------------------------------------------


class HasRolePermission(BasePermission):
    """
    DRF ``BasePermission`` for role-based access control.

    Declare the accepted roles on the view::

        class MyView(APIView):
            permission_classes = [IsAuthenticated, HasRolePermission]
            required_roles = ["admin", "owner"]

    The tenant is resolved (in order) from:
    * ``view.kwargs["tenant_id"]``
    * the ``X-Tenant-ID`` request header
    """

    message = "You do not have the required role to perform this action."

    def has_permission(self, request: Request, view) -> bool:
        required_roles: list[str] = getattr(view, "required_roles", [])
        if not required_roles:
            # View opted out of role enforcement
            return True

        view_kwargs: dict = getattr(view, "kwargs", {}) or {}
        tenant = _resolve_tenant(request, view_kwargs)
        if tenant is None:
            return False

        if not isinstance(request.user, AbstractBaseUser):
            return False
        return RBACService.has_role(request.user, tenant, required_roles)
