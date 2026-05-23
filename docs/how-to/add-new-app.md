# How to add a new Django app

**Story:** SAAS-B03 | **Layer:** L1

This guide walks through adding a **`billing`** app with a thin HTTP layer and a
**`services/billing/`** use-case module — the same pattern as `users`, `tenants`, and `rbac`.

## 1. Scaffold the app

From the project root:

```bash
python manage.py startapp billing apps/billing
```

Create empty package files:

```bash
touch apps/billing/__init__.py
mkdir -p services/billing
touch services/billing/__init__.py
```

Expected layout:

```text
apps/billing/
├── __init__.py
├── apps.py
├── models.py
├── urls.py
├── views.py
└── serializers.py

services/billing/
├── __init__.py
└── invoice_service.py
```

## 2. App config

```python
# apps/billing/apps.py
from django.apps import AppConfig


class BillingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.billing"
```

## 3. Model (optional domain table)

```python
# apps/billing/models.py
import uuid

from django.db import models


class Invoice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    amount_cents = models.PositiveIntegerField()
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.description} ({self.amount_cents}c)"
```

Run migrations after editing models:

```bash
python manage.py makemigrations billing
python manage.py migrate
```

## 4. Service layer (business logic)

```python
# services/billing/invoice_service.py
"""Billing use-cases — no HTTP or DRF dependencies."""

from dataclasses import dataclass

from apps.billing.models import Invoice
from apps.tenants.models import Tenant

from services.exceptions import ValidationServiceError


@dataclass(frozen=True)
class CreateInvoiceInput:
    tenant_id: str
    amount_cents: int
    description: str


class InvoiceService:
    @staticmethod
    def create_invoice(data: CreateInvoiceInput) -> Invoice:
        if data.amount_cents <= 0:
            raise ValidationServiceError("amount_cents must be positive.")
        if not data.description.strip():
            raise ValidationServiceError("description is required.")

        try:
            tenant = Tenant.objects.get(id=data.tenant_id)
        except Tenant.DoesNotExist as exc:
            raise ValidationServiceError("Unknown tenant.") from exc

        return Invoice.objects.create(
            tenant=tenant,
            amount_cents=data.amount_cents,
            description=data.description.strip(),
        )
```

```python
# services/billing/__init__.py
from services.billing.invoice_service import CreateInvoiceInput, InvoiceService

__all__ = ["CreateInvoiceInput", "InvoiceService"]
```

## 5. Serializers and view (HTTP adapter only)

```python
# apps/billing/serializers.py
from rest_framework import serializers

from apps.billing.models import Invoice


class InvoiceCreateSerializer(serializers.Serializer):
    tenant_id = serializers.UUIDField()
    amount_cents = serializers.IntegerField(min_value=1)
    description = serializers.CharField(max_length=255)


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ("id", "tenant_id", "amount_cents", "description", "created_at")
        read_only_fields = fields
```

```python
# apps/billing/views.py
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from services.billing import CreateInvoiceInput, InvoiceService
from services.exceptions import ValidationServiceError

from apps.billing.serializers import InvoiceCreateSerializer, InvoiceSerializer
from apps.rbac.permissions import HasRolePermission


class InvoiceCreateView(APIView):
    """POST /api/v1/billing/<tenant_id>/invoices/ — admin/owner only."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    required_roles = ["admin", "owner"]

    @extend_schema(
        tags=["Billing"],
        request=InvoiceCreateSerializer,
        responses={201: InvoiceSerializer},
        summary="Create an invoice for a tenant",
    )
    def post(self, request, tenant_id):
        serializer = InvoiceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = serializer.validated_data
        try:
            invoice = InvoiceService.create_invoice(
                CreateInvoiceInput(
                    tenant_id=str(tenant_id),
                    amount_cents=payload["amount_cents"],
                    description=payload["description"],
                )
            )
        except ValidationServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)
```

```python
# apps/billing/urls.py
from django.urls import path

from apps.billing.views import InvoiceCreateView

urlpatterns = [
    path(
        "<uuid:tenant_id>/invoices/",
        InvoiceCreateView.as_view(),
        name="billing-invoice-create",
    ),
]
```

## 6. Register the app and URLs

Add the app to `LOCAL_APPS` in `config/settings/base.py`:

```python
LOCAL_APPS = [
    "apps.common",
    "apps.users",
    "apps.authentication",
    "apps.tenants",
    "apps.rbac",
    "apps.notifications",
    "apps.billing",  # ← add
]
```

Mount routes under the v1 API prefix in `config/urls.py`:

```python
path("api/v1/billing/", include("apps.billing.urls")),
```

## 7. Unit test the service (no HTTP)

```python
# tests/unit/services/test_invoice_service.py
import pytest
from apps.billing.models import Invoice
from apps.tenants.models import Tenant
from services.billing import CreateInvoiceInput, InvoiceService
from services.exceptions import ValidationServiceError


@pytest.mark.django_db
def test_create_invoice_success():
    tenant = Tenant.objects.create(name="Acme", slug="acme")

    invoice = InvoiceService.create_invoice(
        CreateInvoiceInput(
            tenant_id=str(tenant.id),
            amount_cents=2500,
            description="Pro plan",
        )
    )

    assert Invoice.objects.count() == 1
    assert invoice.tenant_id == tenant.id
    assert invoice.amount_cents == 2500


@pytest.mark.django_db
def test_create_invoice_rejects_invalid_amount():
    tenant = Tenant.objects.create(name="Acme", slug="acme")

    with pytest.raises(ValidationServiceError, match="amount"):
        InvoiceService.create_invoice(
            CreateInvoiceInput(
                tenant_id=str(tenant.id),
                amount_cents=0,
                description="Bad",
            )
        )
```

## 8. Checklist

- [ ] App listed in `LOCAL_APPS`
- [ ] URLs mounted under `/api/v1/`
- [ ] Business logic in `services/`, not in the view
- [ ] `python manage.py makemigrations` + `migrate`
- [ ] `pytest tests/unit/services/test_invoice_service.py -v`
- [ ] `ruff check .` and `mypy .`

## Related

- [Service layer architecture](../architecture/service-layer.md)
- [Add a new RBAC role](add-new-role.md)
- [Add a Celery task](add-new-celery-task.md)
