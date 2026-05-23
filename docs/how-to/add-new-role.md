# How to add a new RBAC role

**Story:** SAAS-B03 | **Layer:** L1

Roles are **tenant-scoped**: a user can be `admin` in Tenant A and `member` in Tenant B.
This guide adds a **`billing_manager`** role as an example.

## 1. Extend `RoleChoices` and hierarchy

Edit `apps/rbac/models.py`:

```python
class RoleChoices(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    MEMBER = "member", "Member"
    BILLING_MANAGER = "billing_manager", "Billing Manager"


ROLE_HIERARCHY: dict[str, int] = {
    RoleChoices.OWNER: 4,
    RoleChoices.ADMIN: 3,
    RoleChoices.BILLING_MANAGER: 2,
    RoleChoices.MEMBER: 1,
}
```

Create and apply a migration (updates the `role` field choices):

```bash
python manage.py makemigrations rbac
python manage.py migrate
```

`RBACService.VALID_ROLES` is built from `RoleChoices.values`, so the service layer
picks up the new role automatically — no change required in
`services/rbac/rbac_service.py`.

## 2. Protect a view with the new role

Use `HasRolePermission` on class-based DRF views:

```python
# apps/billing/views.py
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.rbac.permissions import HasRolePermission


class InvoiceCreateView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_roles = ["owner", "admin", "billing_manager"]

    def post(self, request, tenant_id):
        ...
```

For function-based views, use the decorator:

```python
from apps.rbac.permissions import require_role


@require_role(["owner", "admin", "billing_manager"])
def export_invoices(request, tenant_id):
    ...
```

Tenant resolution (same as existing endpoints):

1. `tenant_id` in the URL path (preferred)
2. `X-Tenant-ID` request header as fallback

## 3. Assign the role via the service layer

```python
from apps.rbac.models import RoleChoices
from apps.tenants.models import Tenant
from django.contrib.auth import get_user_model
from services.rbac import RBACService

User = get_user_model()

tenant = Tenant.objects.get(slug="tenant1")
user = User.objects.get(username="admin@tenant1.localhost")

RBACService.assign_role(user, tenant, RoleChoices.BILLING_MANAGER)
```

Or via the API (caller must already be `owner` or `admin` in that tenant):

```bash
curl -X POST "http://localhost:8000/api/v1/rbac/<tenant_id>/roles/assign/" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "role": "billing_manager"}'
```

## 4. Test role enforcement

```python
# tests/unit/services/test_billing_manager_role.py
import pytest
from apps.rbac.models import RoleChoices
from apps.tenants.models import Tenant
from django.contrib.auth import get_user_model
from services.rbac import RBACService

User = get_user_model()


@pytest.mark.django_db
def test_assign_billing_manager_role():
    tenant = Tenant.objects.create(name="Acme", slug="acme")
    user = User.objects.create_user(username="finance", password="SecurePass123!")

    RBACService.assign_role(user, tenant, RoleChoices.BILLING_MANAGER)

    assert RBACService.get_role(user, tenant) == RoleChoices.BILLING_MANAGER
    assert RBACService.has_role(user, tenant, ["billing_manager"]) is True
    assert RBACService.has_role(user, tenant, ["admin"]) is False
```

## 5. Optional: seed the role in demo data

If you use `seed_demo`, update `services/demo/seed_service.py` or add a second demo
user in `examples/demo_config.py` and assign `RoleChoices.BILLING_MANAGER` with
`RBACService.assign_role`.

## 6. Checklist

- [ ] `RoleChoices` + `ROLE_HIERARCHY` updated
- [ ] Migration created and applied
- [ ] Views declare `required_roles` including the new role where appropriate
- [ ] Service/assignment tests added
- [ ] OpenAPI descriptions mention the role if the endpoint is public-facing

## Related

- [Add a new app](add-new-app.md)
- [Service layer architecture](../architecture/service-layer.md)
