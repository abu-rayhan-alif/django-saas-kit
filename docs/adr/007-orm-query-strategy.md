# ADR 007 — ORM Query Strategy

**Status:** Accepted  
**Date:** 2026-05-24  
**Story:** NEW-07 | **Layer:** L2

---

## Context

Django SaaS Kit exposes multi-tenant REST endpoints where a single list response can touch several related tables — user accounts, tenant records, role assignments, and notifications.  Without an explicit query strategy, view authors reach for the simplest queryset and inadvertently introduce N+1 patterns that are invisible in unit tests (which hit tiny fixtures) but catastrophic under real data volumes.

Three recurring failure modes motivated this ADR:

1. **N+1 queries** — serializers accessing FK attributes without `select_related` / `prefetch_related`.
2. **Unbounded results** — list endpoints returning full table scans when callers forget `?page_size`.
3. **Missing indexes** — `ORDER BY` and `WHERE` clauses on unindexed columns causing sequential scans as tenant data grows.

---

## Decision

Adopt the following non-negotiable conventions for all new views and services.

### 1. Always resolve FKs eagerly

Every queryset that will be serialised must declare its JOINs up-front:

```python
# FK / OneToOne → select_related (single JOIN)
UserTenantRole.objects.filter(tenant=tenant).select_related("user", "tenant")

# Reverse FK / M2M → prefetch_related (two queries, no JOIN explosion)
Tenant.objects.prefetch_related("user_roles")
```

The serializer layer must **never** trigger implicit DB queries.  If a `SerializerMethodField` does a lookup, it belongs in the queryset annotation or a `Prefetch` object.

### 2. Every list endpoint uses StandardPagination

```python
from apps.common.pagination import StandardPagination

paginator = StandardPagination()          # page_size=20, max=100
page = paginator.paginate_queryset(qs, request)
return paginator.get_paginated_response(serializer_class(page, many=True).data)
```

High-volume append-only feeds (audit log, notification stream) use `CursorPagination` with `ordering` set to an indexed timestamp field.

### 3. Index every filter/sort column

All `ForeignKey` fields carry an implicit index from Django.  Every explicit `filter()` or `order_by()` column that is not a PK must have `db_index=True` or appear in `Meta.indexes`.

### 4. Cache computed aggregates, never raw PII

Cache-aside with an explicit TTL is preferred over object-level caching.  Cache keys must be namespaced by tenant or user ID and must not embed personally-identifiable values.  Invalidate on write within the same service method.

---

## Consequences

**Positive**

- List endpoints stay O(1) in query count regardless of result set size.
- Pagination caps memory usage and response latency independently of data volume.
- Indexed columns keep query plans stable as row counts grow.
- Explicit eager-loading makes DB cost visible in code review.

**Negative**

- `select_related` generates wider rows (all JOIN columns returned); negligible for the column counts in this schema.
- Developers must remember to add eager-loading when extending serializers — enforced by code review checklist, not tooling.
- Cache invalidation adds a step to every write path; missed invalidations cause stale reads (acceptable for non-critical aggregates, not for auth state).

---

## Alternatives

### Lazy loading everywhere (Django default)

Zero boilerplate, but N+1 is guaranteed on any serializer that touches related objects.  **Rejected** — silent performance regression with no test signal.

### GraphQL with DataLoader

DataLoader batches FK lookups automatically.  **Deferred** — introduces a second API layer; REST is the current contract.  Re-evaluate if clients need field-level selection.

### Django ORM query count assertions in every test

`assertNumQueries` on every integration test catches N+1 regressions automatically.  **Partially adopted** — used in performance-sensitive paths; not required everywhere because fixture data is too small to expose the problem reliably.

### Read replicas / CQRS

Route expensive list queries to a read replica.  **Deferred** — premature at current scale; `select_related` + indexing covers the L2 tier.

---

## References

- [Django docs — select_related](https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-related)
- [Django docs — prefetch_related](https://docs.djangoproject.com/en/stable/ref/models/querysets/#prefetch-related)
- [Django docs — Prefetch objects](https://docs.djangoproject.com/en/stable/ref/models/querysets/#prefetch-objects)
- [Performance guide](../performance.md)
