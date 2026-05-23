# ADR 001 — Use PostgreSQL

**Status:** Accepted  
**Date:** 2026-05-23  
**Story:** SAAS-1003

---

## Context

The Django SaaS Kit targets **multi-tenant B2B SaaS**: users, tenant-scoped RBAC, audit fields, UUID primary keys, and relational integrity between tenants and memberships.

We need a database that:

- Supports **ACID transactions** for user registration, role assignment, and billing-style workflows
- Handles **concurrent writers** under Celery workers and multiple Gunicorn processes
- Works well with **Django ORM** and migrations in CI and Docker Compose
- Is a common default for production Django deployments (hosting, backups, extensions)

SQLite is insufficient for production concurrency; serverless-only stores add vendor lock-in for a starter kit meant to be forked.

---

## Decision

Use **PostgreSQL 16** as the sole supported relational database.

| Area | Choice |
|------|--------|
| Driver | `psycopg` v3 (`psycopg[binary]`) |
| Connection | `DATABASE_URL` parsed via `dj-database-url` in `config/env.py` |
| Local dev | PostgreSQL service in `docker-compose.yml` |
| CI | PostgreSQL 16 service container in `.github/workflows/ci.yml` |

All Django models assume PostgreSQL features where needed (UUID, JSONField if used later, standard indexes).

---

## Consequences

**Positive**

- Strong consistency for tenant RBAC and user data
- Mature ecosystem: backups, replication, managed offerings (RDS, Cloud SQL, etc.)
- Django `contrib.postgres` features available if we add them later
- Same DB engine in dev, CI, and production reduces “works on my machine” drift

**Negative**

- Heavier local setup than SQLite (mitigated by Docker Compose `db` service)
- Contributors must run Postgres or use `make dev` with Docker
- Connection pooling and migration discipline required at scale (PgBouncer, zero-downtime migrations) — out of scope for L1 but documented for operators

**Operational**

- Set `DATABASE_URL` in every environment; never commit credentials
- Run `python manage.py migrate` on deploy (entrypoint does this in Docker)

---

## Alternatives

### SQLite

**Rejected** for production: file-level locking, poor fit for multiple app replicas and Celery workers writing concurrently. Acceptable only for throwaway local experiments outside this kit’s supported path.

### MySQL / MariaDB

**Rejected** for this starter: equally capable for Django, but the team standardized on PostgreSQL for JSON operators, extension ecosystem, and alignment with most SaaS hosting examples. Forks may swap with an ADR if required.

### Serverless SQL (e.g. Neon, PlanetScale)

**Deferred** — viable for deploy targets; the kit stays ORM- and Postgres-compatible so adapters can be documented in deployment guides without changing application code.

---

## References

- [Django databases — PostgreSQL](https://docs.djangoproject.com/en/stable/ref/databases/#postgresql-notes)
- [psycopg 3 documentation](https://www.psycopg.org/psycopg3/docs/)
