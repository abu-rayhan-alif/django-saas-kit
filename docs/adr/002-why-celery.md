# ADR 002 — Why Celery

**Status:** Accepted  
**Date:** 2026-05-23  
**Story:** SAAS-501 / SAAS-1003

---

## Context

SaaS workloads need **asynchronous work**: sending email, webhooks, report generation, and periodic maintenance (e.g. expiring JWT blacklist rows). HTTP requests must stay fast; long or unreliable I/O belongs off the request thread.

Requirements for the starter kit:

- Works with **Redis** already required for cache
- Integrates with **Django** (settings, ORM in tasks, `shared_task`)
- Supports **scheduled** jobs (cron-like) for ops tasks
- Familiar to Django teams and documented in Docker Compose (`celery`, `celery-beat`)

---

## Decision

Use **Celery 5** with **Redis** as the message broker and result backend, plus **django-celery-beat** with the database scheduler for periodic tasks.

| Component | Configuration |
|-----------|----------------|
| App | `config/celery.py` — `app.autodiscover_tasks()` |
| Broker | `CELERY_BROKER_URL` (default Redis DB `1`) |
| Results | `CELERY_RESULT_BACKEND` (default Redis DB `2`) |
| Beat | `celery-beat` service + `config/celery.py` `beat_schedule` |
| Workers | `celery -A config worker` in `docker-compose.yml` |

**Example tasks (SAAS-501):**

| Task | Module | Trigger |
|------|--------|---------|
| `send_welcome_email` | `apps/users/tasks.py` | `UserService.create_user` → `.delay(user_id)` |
| `cleanup_expired_tokens` | `apps/authentication/tasks.py` | Beat daily 03:00 UTC |

Register DB-backed beat entries after migrate:

```bash
python manage.py sync_beat_schedule
```

Business logic invoked from tasks lives in **`services/`**; `tasks.py` files stay thin wrappers.

---

## Consequences

**Positive**

- Mature task retries, routing, and monitoring integrations (Flower, Sentry, etc.)
- Large community and Django-specific examples
- Beat + DB scheduler allows changing schedules without redeploying code
- Same Redis instance can serve cache, broker, and results on logical DB indexes

**Negative**

- Operational complexity: workers and beat must run in production alongside web processes
- Result backend can fill Redis if tasks store large payloads — prefer storing IDs and re-fetching from Postgres
- Cold start and visibility debugging harder than synchronous code

**Operational**

- Scale workers independently of web replicas
- Use `CELERY_TASK_ALWAYS_EAGER` in tests (see how-to Celery guide)
- Monitor queue depth and failed tasks in production

---

## Alternatives

### Django-RQ (Redis Queue)

RQ is simpler: Redis-only, fewer concepts (no separate result backend required for basic use), lighter mental model.

**Rejected** for this kit because:

- We already need **periodic scheduling**; RQ requires `rq-scheduler` or cron sidecars, while Celery Beat is first-class
- Celery is the more common choice in Django SaaS tutorials and hiring markets
- Multi-queue and retry policies are more standardized in Celery

**When RQ wins:** small apps with a handful of fire-and-forget jobs and no beat.

### Redis Streams (consumer groups)

Using Redis Streams directly (or `redis-py` consumers) gives a durable log and consumer groups without Celery’s framework.

**Rejected** because:

- No built-in Django integration, task discovery, or retry semantics — we would rebuild Celery-like plumbing
- Higher implementation cost for a **starter kit** optimized for productivity
- Beat/scheduling still needs a separate solution

**When Streams win:** high-throughput event pipelines, strict ordering per stream, or polyglot consumers not using Python workers.

### Dramatiq, Huey, ARQ

Other Python task queues with varying simplicity.

**Deferred** — viable alternatives; not chosen to avoid splitting documentation and Compose examples. Forks can add an ADR if switching.

### Synchronous / `threading` in request cycle

**Rejected** — blocks Gunicorn workers, no durability on process crash, poor fit for email and webhooks.

---

## References

- [Celery documentation](https://docs.celeryq.dev/)
- [django-celery-beat](https://django-celery-beat.readthedocs.io/)
- [How to add a Celery task](../how-to/add-new-celery-task.md)
