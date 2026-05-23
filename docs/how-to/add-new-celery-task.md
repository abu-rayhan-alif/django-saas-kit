# How to add a new Celery task

**Story:** SAAS-501 / SAAS-B03 | **Layer:** L1

**Built-in examples:** `send_welcome_email` (`apps/users/tasks.py`), `cleanup_expired_tokens` (`apps/authentication/tasks.py`, daily beat).

**Retry & idempotency:** see [Background jobs](../background-jobs.md) (SAAS-502).

Background work runs through **Celery**. The worker is already defined in `docker-compose.yml`
(`celery` and `celery-beat` services). Tasks are auto-discovered from `tasks.py` in each
installed Django app (`config/celery.py` → `app.autodiscover_tasks()`).

Keep **business logic in `services/`**; tasks should be thin wrappers that call services.

## 1. Define the task

Create `apps/billing/tasks.py` (replace `billing` with your app name):

```python
# apps/billing/tasks.py
import logging

from celery import shared_task
from services.billing import InvoiceService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_invoice_reminder(self, invoice_id: str) -> str:
    """
    Example async job — loads an invoice and performs a side effect.

    ``bind=True`` exposes ``self`` for retries.
    """
    try:
        InvoiceService.send_payment_reminder(invoice_id)
    except Exception as exc:
        logger.exception("Invoice reminder failed for %s", invoice_id)
        raise self.retry(exc=exc) from exc

    return f"reminder_sent:{invoice_id}"
```

Add the service method the task delegates to:

```python
# services/billing/invoice_service.py  (add to existing InvoiceService)
from apps.billing.models import Invoice

from services.exceptions import ValidationServiceError


class InvoiceService:
    # ... create_invoice() from add-new-app.md ...

    @staticmethod
    def send_payment_reminder(invoice_id: str) -> None:
        try:
            invoice = Invoice.objects.select_related("tenant").get(id=invoice_id)
        except Invoice.DoesNotExist as exc:
            raise ValidationServiceError("Invoice not found.") from exc

        # Replace with real email/notification integration
        print(f"Reminder: pay invoice {invoice.id} for tenant {invoice.tenant.slug}")
```

## 2. Trigger the task from a view (optional)

```python
# apps/billing/views.py
from rest_framework import status
from rest_framework.response import Response

from apps.billing.tasks import send_invoice_reminder


class InvoiceReminderView(APIView):
    def post(self, request, tenant_id, invoice_id):
        send_invoice_reminder.delay(str(invoice_id))
        return Response({"detail": "Reminder queued."}, status=status.HTTP_202_ACCEPTED)
```

`.delay()` enqueues the job; the HTTP response returns immediately.

## 3. Run the worker and beat

**Docker (recommended):**

```bash
docker compose up -d celery celery-beat
docker compose logs -f celery
docker compose logs -f celery-beat
```

Beat registers the daily `cleanup_expired_tokens` schedule via `python manage.py sync_beat_schedule` on startup (see `config/celery.py`).

**Local shell:**

```bash
celery -A config worker -l info
```

Ensure `.env` includes Redis URLs (see `.env.example`):

```env
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

## 4. Schedule a periodic task (optional)

This project uses **django-celery-beat** with the database scheduler. After migrations,
register a schedule in Django admin (**Periodic tasks**) or in code:

```python
# apps/billing/tasks.py
from celery.schedules import crontab
from config.celery import app


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(hour=9, minute=0),  # every day at 09:00
        send_daily_invoice_digest.s(),
        name="billing-daily-digest",
    )


@shared_task
def send_daily_invoice_digest() -> str:
    # InvoiceService.build_daily_digest() etc.
    return "ok"
```

Start **celery-beat** alongside the worker (`docker compose` already includes `celery-beat`).

## 5. Test tasks synchronously

In tests, run tasks eagerly so no broker is required:

```python
# tests/unit/test_invoice_tasks.py
import pytest
from apps.billing.models import Invoice
from apps.billing.tasks import send_invoice_reminder
from apps.tenants.models import Tenant


@pytest.mark.django_db
def test_send_invoice_reminder_task(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    tenant = Tenant.objects.create(name="Acme", slug="acme")
    invoice = Invoice.objects.create(
        tenant=tenant, amount_cents=1000, description="Test",
    )

    result = send_invoice_reminder.delay(str(invoice.id))
    assert result.successful()
    assert result.result == f"reminder_sent:{invoice.id}"
```

Add to `config/settings/local.py` or a `pytest` fixture if you want eager mode for all tests:

```python
# conftest.py (optional)
import pytest


@pytest.fixture(autouse=True)
def celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
```

## 6. Manual smoke test

```bash
python manage.py shell
```

```python
from apps.billing.tasks import send_invoice_reminder

send_invoice_reminder.delay("00000000-0000-4000-8000-000000000099")
```

Watch the worker logs for the printed reminder line or any traceback.

## 7. Checklist

- [ ] Task lives in `apps/<app>/tasks.py` (auto-discovered)
- [ ] Task calls `services/`, not ORM-heavy logic inline
- [ ] Retries/logging configured for flaky IO (email, webhooks)
- [ ] Worker + Redis running (`docker compose up celery`)
- [ ] Unit test uses `CELERY_TASK_ALWAYS_EAGER`

## Related

- [Add a new app](add-new-app.md)
- [Celery configuration](../../config/celery.py)
- [docker-compose.yml](../../docker-compose.yml) — `celery` and `celery-beat` services
