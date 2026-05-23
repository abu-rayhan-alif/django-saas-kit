# ADR 004 — Why Redis

**Status:** Accepted  
**Date:** 2026-05-23  
**Story:** SAAS-1003

---

## Context

The stack needs:

1. A **fast cache** for Django (sessions optional later, view caching, rate limits)
2. A **message broker** for Celery (see [ADR 002](002-why-celery.md))
3. A **result backend** for Celery task outcomes (optional but configured by default)

Running three separate infrastructure products for L1 would increase Docker Compose and onboarding cost. We want one in-memory data store that teams already know and that scales from laptop to production.

---

## Decision

Use **Redis 7** for cache, Celery broker, and Celery results, with **logical database indexes** on a single instance in development:

| Use | Env var | Default (Compose) |
|-----|---------|-------------------|
| Django cache | `REDIS_URL` | `redis://redis:6379/0` |
| Celery broker | `CELERY_BROKER_URL` | `redis://redis:6379/1` |
| Celery results | `CELERY_RESULT_BACKEND` | `redis://redis:6379/2` |

Django cache backend: `django.core.cache.backends.redis.RedisCache` in `config/settings/base.py`.

`REDIS_URL` is **required** at startup (with `SECRET_KEY` and `DATABASE_URL`).

---

## Consequences

**Positive**

- Single Redis container in `docker-compose.yml` covers cache + async messaging
- Sub-millisecond reads for hot keys; reduces PostgreSQL load for cacheable reads
- Wide managed-service support (ElastiCache, Redis Cloud, Upstash, etc.)
- Simple local dev: one port `6379`

**Negative**

- Another moving part in production (persistence, failover, memory limits)
- Data in Redis is ephemeral unless persistence (AOF/RDB) is configured — cache loss is acceptable; broker message loss depends on durability settings
- Logical DB separation is not hard isolation; production may prefer separate instances per concern

**Operational**

- Monitor memory usage and eviction policy
- Use TLS and AUTH in production
- Consider separate Redis instances for cache vs broker at scale

---

## Alternatives

### Memcached (cache only)

Memcached is excellent for pure caching and simpler than Redis for that single role.

**Rejected** as the only store because we still need a **message broker** for Celery; we would run Memcached + Redis anyway. Redis covers both cache and broker.

### RabbitMQ (broker only)

RabbitMQ is a robust AMQP broker with strong delivery guarantees.

**Rejected** for L1 to avoid a second service in Compose and cognitive overhead. Celery + Redis is the default Django SaaS path documented in this kit. High-reliability forks can adopt RabbitMQ with a new ADR.

### PostgreSQL as Celery broker

Possible via experimental backends; not mainstream.

**Rejected** — adds DB load and lacks Redis cache performance profile.

### In-process cache (`LocMemCache`)

Used only in `config/settings/mypy.py` for type-checking without Redis.

**Rejected** for runtime — not shared across Gunicorn workers or Celery.

### KeyDB / Valkey

Redis-compatible alternatives.

**Deferred** — drop-in replacements for deployment; no starter-kit code change required.

---

## References

- [Django Redis cache backend](https://docs.djangoproject.com/en/stable/topics/cache/#redis)
- [Celery — Using Redis](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html)
- [ADR 002 — Why Celery](002-why-celery.md)
