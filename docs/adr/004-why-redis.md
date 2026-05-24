# ADR 004 — Why Redis for Cache, Broker, and Result Backend

**Status:** Accepted
**Date:** 2026-05-23
**Deciders:** Platform team
**Story:** SAAS-401

---

## Context

The Django SaaS Kit requires three infrastructure capabilities beyond the primary database:

1. **A message broker** — to dispatch background tasks to Celery workers.
2. **A result backend** — to store and retrieve Celery task outcomes.
3. **An application cache** — to accelerate repeated reads (e.g. permission checks, session data).

Deploying three separate backing services for these three concerns adds operational overhead. We evaluated whether a single service could cover all three without meaningful trade-offs.

---

## Decision

Use **Redis 7** for all three roles:

| Role | Django / Celery setting | Redis DB index |
|------|------------------------|----------------|
| Application cache | `CACHES["default"]` | 0 |
| Celery broker | `CELERY_BROKER_URL` | 1 |
| Celery result backend | `CELERY_RESULT_BACKEND` | 2 |

Separate logical databases (0 / 1 / 2) provide namespace isolation without requiring separate processes or ports.

### Configuration

```python
# config/settings/base.py
REDIS_URL = get_str("REDIS_URL", required=True)          # e.g. redis://redis:6379/0
CELERY_BROKER_URL    = get_str("CELERY_BROKER_URL",    default=REDIS_URL)
CELERY_RESULT_BACKEND = get_str("CELERY_RESULT_BACKEND", default=REDIS_URL)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}
```

In `docker-compose.yml` a single `redis:7-alpine` service satisfies all three URLs.

---

## Alternatives Considered

### RabbitMQ as broker + Redis as cache

RabbitMQ is the gold-standard Celery broker: AMQP protocol, per-queue durability, dead-letter exchanges, sophisticated routing. However:

- Requires operating a second stateful service alongside Redis.
- AMQP adds complexity (exchanges, bindings, vhosts) that our simple task queue does not need.
- Result backend cannot be RabbitMQ itself — still requires Redis or a DB.

**Deferred** — RabbitMQ is the right upgrade path if task routing or guaranteed delivery at scale becomes a requirement. Because `CELERY_BROKER_URL` is an env-var, switching is a one-line config change with no code changes.

### Database-backed broker (`django-db-geventpool` / `django-celery-results`)

Using PostgreSQL as the Celery broker eliminates Redis entirely. Django ships `django.core.cache.backends.db.DatabaseCache`; Celery supports `django-db-geventpool` and similar.

- Every task dispatch becomes a DB write; every worker poll is a DB read. This competes with application traffic.
- Polling latency is higher than a pub/sub in-memory store.
- Suitable only for very low task volume; does not scale horizontally.

**Rejected** — introduces per-task database round-trips that undermine the stateless scaling goal.

### Memcached as cache

Memcached is a battle-tested, high-performance cache. It cannot serve as a broker or result backend, so Redis would still be required for Celery.

**Rejected** — running Memcached alongside Redis doubles the cache infrastructure for no gain in our use case. Redis cache performance is equivalent for our workload.

### Valkey / KeyDB

Drop-in Redis forks with slightly different licensing or clustering models. Fully compatible at the protocol level.

**Deferred** — Valkey is tracked as a future drop-in replacement if Redis licensing becomes a concern. The Docker image name is the only change required.

---

## Consequences

**Positive**

- Single service covers all three roles → simpler `docker-compose.yml`, fewer `HEALTHCHECK` entries, one backup/restore procedure.
- In-memory store means sub-millisecond cache reads and near-instant task dispatch.
- Logical DB isolation (index 0 / 1 / 2) prevents cache flushes from accidentally clearing broker state.
- Redis Streams (available in Redis 5+) provide a migration path to durable task queues if needed.
- `redis:7-alpine` image is small (~40 MB) and has a predictable CVE surface.

**Negative / Trade-offs**

- Redis is an in-memory store. A crash without `appendonly yes` / RDB snapshots may lose pending tasks and cached data. For dev this is acceptable; production deployments should enable Redis persistence or use a managed Redis service (ElastiCache, Upstash, Redis Cloud).
- A single Redis instance is a single point of failure. HA requires Redis Sentinel or Cluster — out of scope for this starter kit but documented here for operators.
- Memory is finite. Large Celery result payloads stored in Redis inflate memory usage. Set `CELERY_RESULT_EXPIRES` to expire old results automatically.

---

## References

- [Redis documentation](https://redis.io/docs/)
- [Celery — Redis broker](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html)
- [Django — Redis cache backend](https://docs.djangoproject.com/en/5.1/topics/cache/#redis)
- [ADR 002 — Why Celery](002-why-celery.md)
