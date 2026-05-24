# Performance Guide

This document covers the query patterns, indexing strategy, pagination contract, and caching approach used in Django SaaS Kit.  Each section leads with a rule, then a concrete example from the codebase.

---

## 1. The N+1 Problem

### What it is

An N+1 query occurs when code fetches a list of N rows and then fires an extra query **for each row** to load a related object — N lists + 1 per row = N+1 round-trips.  In a SaaS API with dozens of tenant roles or hundreds of notifications, a single list endpoint can silently execute hundreds of SQL statements.

### Before — naive loop (broken)

```python
# apps/rbac/views.py  ← DO NOT write this
def get(self, request, tenant_id):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    roles = UserTenantRole.objects.filter(tenant=tenant)   # 1 query

    data = []
    for role in roles:
        data.append({
            "role": role.role,
            "username": role.user.username,      # +1 query per row  ← N+1
            "tenant_name": role.tenant.name,     # +1 query per row  ← N+1
        })
    return Response(data)
```

For a tenant with 50 members this fires **101 queries** (1 for roles + 50 for users + 50 for tenant).

### After — `select_related` (correct)

```python
# apps/rbac/views.py  ← actual implementation
def get(self, request, tenant_id):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    roles = (
        UserTenantRole.objects
        .filter(tenant=tenant)
        .select_related("user", "tenant")   # JOIN — always 1 query
    )
    serializer = UserTenantRoleSerializer(roles, many=True)
    return Response(serializer.data)
```

`select_related` issues a single SQL `JOIN`.  Use it whenever you traverse a **ForeignKey or OneToOneField**.

---

## 2. `select_related` vs `prefetch_related`

### When to use each

| Situation | Tool | SQL issued |
|-----------|------|------------|
| Traverse a **ForeignKey / OneToOne** on each row | `select_related` | 1 `JOIN` |
| Fetch a **reverse FK** or **ManyToMany** set per row | `prefetch_related` | 1 + 1 (main + relation) |
| Mix: FK on main + reverse FK on each result | Both together | 2 queries total |

### `select_related` — FK traversal

The RBAC list view selects both `user` and `tenant` in one shot:

```python
UserTenantRole.objects
    .filter(tenant=tenant)
    .select_related("user", "tenant")
```

Generated SQL:

```sql
SELECT utr.*, u.*, t.*
FROM rbac_usertenantrole utr
INNER JOIN auth_user u ON utr.user_id = u.id
INNER JOIN tenants_tenant t ON utr.tenant_id = t.id
WHERE utr.tenant_id = %s;
```

### `prefetch_related` — reverse FK / M2M

Fetch all tenants and, for each, the set of role assignments in **two** queries:

```python
# 2 queries regardless of how many tenants there are
tenants = Tenant.objects.prefetch_related("user_roles")

for tenant in tenants:
    # tenant.user_roles.all() hits Python, not the database
    for role in tenant.user_roles.all():
        print(role.role)
```

### `Prefetch` with a filtered sub-queryset

When you need only a subset of the related records:

```python
from django.db.models import Prefetch
from apps.notifications.models import Notification

users = User.objects.prefetch_related(
    Prefetch(
        "notifications",
        queryset=Notification.objects.filter(is_read=False).order_by("-created_at"),
        to_attr="unread_notifications",   # stored on each user object
    )
)

for user in users:
    print(user.unread_notifications)   # list — no extra query
```

### Checking your query count

Use Django's query logger in the shell or tests:

```python
from django.db import connection, reset_queries
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def test_no_n_plus_one():
    reset_queries()
    response = client.get("/api/v1/rbac/<tenant_id>/roles/")
    assert len(connection.queries) <= 3   # auth + tenant lookup + roles JOIN
```

Or add `django-debug-toolbar` to `LOCAL_APPS` in `config/settings/local.py` for a browser-side query inspector.

---

## 3. Pagination

### Rule

**Every list endpoint must paginate.**  Returning unbounded querysets transfers the ORM cost and network payload to the caller and can exhaust memory under load.

### How it works in this project

All list views use `StandardPagination` (`apps/common/pagination.py`):

```python
class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
```

Response envelope:

```json
{
    "count": 143,
    "next": "https://api.example.com/api/v1/notifications/?page=2",
    "previous": null,
    "results": [...]
}
```

### Adding pagination to a new view

```python
from apps.common.pagination import StandardPagination

class MyListView(APIView):
    def get(self, request):
        qs = MyModel.objects.filter(owner=request.user).select_related("tenant")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(MySerializer(page, many=True).data)
```

### Cursor pagination for high-volume feeds

For append-only tables (notifications, audit logs) with millions of rows, replace `PageNumberPagination` with `CursorPagination`.  Offset-based pagination degrades as `OFFSET` grows; cursor pagination stays O(log N):

```python
from rest_framework.pagination import CursorPagination

class NotificationCursorPagination(CursorPagination):
    page_size = 50
    ordering = "-created_at"   # must match a db_index field
```

---

## 4. Indexing Strategy

### Rule

Index every field used in `WHERE`, `ORDER BY`, or `JOIN ON` clauses that is not a primary key.  Do not add indexes speculatively — each index costs one write per insert/update.

### Indexes already in this project

| Model | Field | Why |
|-------|-------|-----|
| `Notification` | `user` (FK) | Filter by owner on every request |
| `Notification` | `is_read` | `filter(is_read=False)` list |
| `Notification` | `created_at` | `ORDER BY -created_at` cursor pagination |
| `UserTenantRole` | `role` | Role-based permission checks |
| `UserTenantRole` | `created_at` | Ordered role list |
| `BaseModel` subclasses | `created_at`, `is_deleted` | Soft-delete filter + ordering |

All of these use `db_index=True` in the field declaration:

```python
is_read = models.BooleanField(default=False, db_index=True)
created_at = models.DateTimeField(auto_now_add=True, db_index=True)
```

### Composite indexes for multi-column filters

When you consistently filter on two columns together, a composite index beats two single-column indexes:

```python
class Meta:
    indexes = [
        models.Index(fields=["user", "is_read"], name="notif_user_unread_idx"),
    ]
```

### Checking slow queries

In development, enable Django's slow-query logging:

```python
# config/settings/local.py
LOGGING["loggers"]["django.db.backends"] = {
    "level": "DEBUG",
    "handlers": ["console"],
}
```

In production, use `pg_stat_statements` or `EXPLAIN ANALYZE` to identify missing indexes.

---

## 5. Caching

### Rule

Cache data that is: (a) expensive to compute, (b) read far more often than written, and (c) tolerable to be slightly stale.  Never cache user-specific PII without a per-user cache key.

### Cache backend

Redis is already configured as the default cache (`config/settings/base.py`):

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}
```

### Pattern 1 — cache-aside for a computed value

```python
from django.core.cache import cache

def get_tenant_member_count(tenant_id: str) -> int:
    key = f"tenant:{tenant_id}:member_count"
    count = cache.get(key)
    if count is None:
        count = UserTenantRole.objects.filter(tenant_id=tenant_id).count()
        cache.set(key, count, timeout=300)   # 5-minute TTL
    return count
```

### Pattern 2 — invalidate on write

```python
def assign_role(user, tenant, role, *, assigned_by):
    # ... create/update UserTenantRole ...
    cache.delete(f"tenant:{tenant.pk}:member_count")   # invalidate
```

### Pattern 3 — per-request cache with `cached_property`

For data used multiple times **within a single request** but never shared across requests:

```python
from functools import cached_property

class RBACService:
    @cached_property
    def roles_for_user(self):
        return list(UserTenantRole.objects.filter(user=self.user).select_related("tenant"))
```

### What NOT to cache

- Raw querysets (they are lazy — cache the evaluated list or scalar)
- Passwords, tokens, or any PII
- Data with sub-second write frequency (cache churn wastes Redis bandwidth)

---

## 6. Quick Reference

| Problem | Fix |
|---------|-----|
| N+1 on FK traversal | `.select_related("fk_field")` |
| N+1 on reverse FK / M2M | `.prefetch_related("reverse_name")` |
| Filtered reverse relation | `Prefetch("name", queryset=..., to_attr=...)` |
| Unbounded list response | `StandardPagination` (default) or `CursorPagination` (high-volume) |
| Slow `WHERE` / `ORDER BY` | `db_index=True` or `Meta.indexes` composite |
| Expensive repeated computation | `cache.get` / `cache.set` with explicit TTL |
| Request-scoped repeated computation | `@cached_property` on service object |

See [ADR 007](adr/007-orm-query-strategy.md) for the rationale behind these choices.
