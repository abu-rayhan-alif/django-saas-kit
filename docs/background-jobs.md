# Background jobs — retry, idempotency, and dead letters

**Story:** SAAS-502 / L2 background jobs | **Layer:** L2

This guide documents how **Celery** tasks should handle failures, retries, and duplicate
delivery in django-saas-kit. **No new production code is required** to satisfy this
document — optional reference implementations may exist in the repo (`apps/common/celery_policy.py`,
`services/common/idempotency.py`, `apps/users/tasks.py`).

---

## Retry strategy

### Policy (default for retriable tasks)

| Setting | Value | Meaning |
|---------|-------|---------|
| `max_retries` | **3** | Up to 3 retries after the first failure (4 attempts total) |
| `retry_backoff` | **True** | Exponential delay between retries (`2^retry_count` seconds, capped) |
| `retry_backoff_max` | **600** | Maximum wait between retries (10 minutes) |
| `retry_jitter` | **True** | Random jitter to avoid thundering herd |
| `autoretry_for` | `(Exception,)` | Retry on any exception (narrow in production if needed) |

Defined in code as `TASK_RETRY_DECORATOR_KWARGS` in `apps/common/celery_policy.py`.

**Example task:** `send_welcome_email` in `apps/users/tasks.py`.

```python
from apps.common.celery_policy import TASK_RETRY_DECORATOR_KWARGS
from celery import shared_task

@shared_task(name="apps.users.tasks.send_welcome_email", **TASK_RETRY_DECORATOR_KWARGS)
def send_welcome_email(self, user_id: int) -> str:
    ...
```

### When **not** to retry

- **Periodic maintenance** (e.g. `cleanup_expired_tokens`) — fail visibly; fix ops issue
- **Validation errors** — bad input will not succeed on retry; catch and log, do not autoretry
- **Non-idempotent side effects** without an idempotency key — fix idempotency first

### Exponential backoff example

With `retry_backoff=True` and `retry_backoff_max=600`, Celery uses **exponential delay**
between attempts (approximately `2^retry_number` seconds, plus jitter). Example timeline
for `send_welcome_email` when SMTP fails twice then succeeds:

| Attempt | Result | Wait before next try (approx.) |
|---------|--------|--------------------------------|
| 1 | `ConnectionError` | — |
| 2 | `ConnectionError` | ~2s (2¹ + jitter) |
| 3 | Success | ~4s (2² + jitter) after 2nd failure |
| 4 | *(not run)* | — |

If all **3 retries** are exhausted (4 failed attempts total), the task ends in **FAILURE**
and should surface via logs / DLQ pattern below.

Manual retry decorator (equivalent idea without autoretry):

```python
@shared_task(bind=True, max_retries=3)
def my_task(self):
    try:
        do_work()
    except TransientError as exc:
        # countdown=2 ** self.request.retries  → 1s, 2s, 4s, …
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

### Observing retries

```bash
docker compose logs -f celery
```

Failed tasks after all retries remain in the result backend with `FAILURE` state when
`CELERY_RESULT_BACKEND` is enabled.

---

## Idempotency key pattern

Celery **at-least-once** delivery means a task may run more than once. Any side effect
(email, charge, webhook) must be **idempotent**.

### Key format

```text
{task_name}:{business_id}
```

| Task | Key example |
|------|-------------|
| Welcome email | `welcome_email:42` |
| Invoice paid webhook | `invoice_paid:inv_9f3a2c` |

### Implementation

Use `IdempotencyService` (`services/common/idempotency.py`):

```python
from services.common.idempotency import IdempotencyService

idempotency_key = IdempotencyService.build_key("welcome_email", user_id)

return IdempotencyService.run(
    idempotency_key,
    lambda: WelcomeEmailService.send_to_user(user_id),
)
```

- First run executes the lambda and stores the return value in **Redis cache** (24h TTL).
- Duplicate runs (retry or double `.delay()`) return the cached result without re-sending email.

### Guidelines

1. Choose a **stable business id** (user pk, payment id), not Celery `task_id`.
2. Set TTL longer than your max retry window + queue lag.
3. For “exactly once” money movement, use DB unique constraints in addition to cache keys.

---

## Dead letter queue (concept)

Redis (our broker) does not provide a built-in dead letter queue (DLQ) like RabbitMQ.
When all retries are exhausted, the task is marked **failed**. Operators should:

| Approach | Description |
|----------|-------------|
| **Failed result + logs** | Inspect Celery logs and result backend; re-run manually after fix |
| **Dedicated DLQ queue** | Route `on_failure` signal to enqueue `dead_letter.{task_name}` for human review |
| **Monitoring alert** | Sentry / CloudWatch on task failure rate |
| **Beat reconciliation** | Periodic job lists stuck `FAILURE` results and opens an issue |

### Recommended production pattern

1. Connect Celery `task_failure` signal → structured log + alert.
2. Persist failure payload (task name, args, traceback) to a `FailedTask` admin table or external queue.
3. Provide a management command `retry_failed_task <id>` for safe replay **after** fixing root cause.

This starter kit documents the pattern; a full DLQ table is left for product forks.

---

## Testing

Tests use **`CELERY_TASK_ALWAYS_EAGER=True`** (see `tests/conftest.py`) so tasks run
inline without a live broker. Retry behaviour is covered in `tests/unit/test_task_retry.py`.

```bash
pytest tests/unit/test_task_retry.py -v
```

---

## Related

- [ADR 002 — Why Celery](adr/002-why-celery.md)
- [How to add a Celery task](how-to/add-new-celery-task.md)
- [Celery configuration](../config/celery.py)
