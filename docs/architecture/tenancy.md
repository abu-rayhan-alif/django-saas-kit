# Tenancy Architecture — Subdomain Routing

**Story:** SAAS-T01 | **Layer:** L1

---

## Overview

Django SaaS Kit uses a **single-database, shared-schema** multi-tenancy model. All tenants share the same PostgreSQL database and the same table set. Tenant isolation is enforced at the application layer, not at the database layer.

```
tenant1.localhost  ─┐
                    ├──► TenantMiddleware ──► Domain table ──► Tenant row ──► request.tenant
tenant2.localhost  ─┘
```

---

## Data Model

### `Tenant`

The core workspace entity.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `name` | CharField | Display name |
| `slug` | SlugField (unique) | API path identifier |
| `schema_name` | SlugField (unique) | Canonical subdomain identifier |
| `is_active` | BooleanField | Gates access — inactive tenants receive 403 |
| `created_at` | DateTimeField | Auto-set on creation |
| `updated_at` | DateTimeField | Auto-updated on save |

### `Domain`

Maps a hostname to a tenant. A tenant can have multiple domains (e.g. vanity domains), but exactly one should be marked `is_primary = True`.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `tenant` | FK → Tenant | CASCADE on tenant delete |
| `domain` | CharField (unique) | Full hostname, e.g. `tenant1.localhost` |
| `is_primary` | BooleanField | Marks the canonical domain |

---

## Middleware — `TenantMiddleware`

**Location:** `apps/tenants/middleware.py`  
**Position in stack:** immediately after `RequestContextMiddleware`, before all other app middleware.

```
SecurityMiddleware
CorsMiddleware
RequestContextMiddleware      ← binds request_id
TenantMiddleware              ← binds tenant_id
WhiteNoiseMiddleware
SessionMiddleware
...
```

### Resolution algorithm

```
request.get_host()
  │
  ▼
strip port  ("tenant1.localhost:8000" → "tenant1.localhost")
  │
  ▼
Domain.objects.get(domain=host)
  │            │
  │         DoesNotExist → 404 {"error": "not_found"}
  │
  ▼
domain.tenant.is_active?
  │            │
  │         False → 403 {"error": "tenant_inactive"}
  │
  ▼
request.tenant = tenant
structlog.bind(tenant_id=tenant.id)
  │
  ▼
get_response(request)
```

### Exempt paths

The following prefixes bypass tenant resolution and receive `request.tenant = None`. They are safe to hit on any hostname (useful for health checks and the admin interface).

| Prefix | Reason |
|--------|--------|
| `/admin/` | Django admin runs on the base domain |
| `/health/` | Load-balancer health probes |
| `/ready/` | Readiness probe |
| `/api/docs/` | Swagger UI |
| `/api/schema/` | OpenAPI schema |
| `/api/redoc/` | ReDoc |
| `/static/` | Whitenoise static files |

---

## Service — `TenantService.create_tenant()`

**Location:** `services/tenants/tenant_service.py`

Creates a `Tenant` and its first `Domain` atomically in a single transaction. This is the only supported way to create tenants in application code — direct `Tenant.objects.create()` bypasses validation and leaves the tenant without a domain (unreachable via the middleware).

```python
from services.tenants import TenantService

result = TenantService.create_tenant(
    name="Acme Corp",
    schema_name="acme",        # → acme.localhost
    domain="acme.localhost",
)

result.tenant   # Tenant instance
result.domain   # Domain instance
```

Raises `ValidationServiceError` for an invalid `schema_name` and `ConflictServiceError` if the `schema_name` or `domain` is already taken.

---

## Local Development

Add entries to your system hosts file so that subdomains resolve to `127.0.0.1`:

**Linux / macOS** (`/etc/hosts`):

```
127.0.0.1   tenant1.localhost
127.0.0.1   tenant2.localhost
```

**Windows** (`C:\Windows\System32\drivers\etc\hosts`):

```
127.0.0.1   tenant1.localhost
127.0.0.1   tenant2.localhost
```

Then seed the tenants via Django shell or the `seed_demo` command:

```python
from services.tenants import TenantService

TenantService.create_tenant("Tenant One", "tenant1", "tenant1.localhost")
TenantService.create_tenant("Tenant Two", "tenant2", "tenant2.localhost")
```

Requests to `http://tenant1.localhost:8000/api/v1/` will now resolve `request.tenant` to the Tenant One workspace.

---

## Design Decisions

### Why shared schema rather than per-tenant schemas?

Per-tenant PostgreSQL schemas (as used by `django-tenants`) require schema-aware migrations, separate connection routing, and a `TENANT_APPS` / `SHARED_APPS` split. This adds significant operational complexity for a starter kit. Shared schema with application-layer isolation is simpler to understand, easier to migrate, and sufficient for most SaaS products up to tens of thousands of tenants.

See the [performance guide](../performance.md) for indexing strategies that keep shared-schema queries fast.

### Why a separate `Domain` table rather than a subdomain field on `Tenant`?

A dedicated `Domain` table allows:
- Multiple hostnames per tenant (vanity domains, `www.` aliases)
- Clean migration if a tenant changes their primary domain
- A single indexed lookup that covers both subdomain and custom-domain routing without conditional logic in the middleware

### Why not `django-tenants` or `django-tenant-schemas`?

Both libraries force per-tenant PostgreSQL schemas. While powerful for strong data isolation, they require modifying every migration and all ORM queries. For an L1 starter kit that teams will extend, the application-layer approach is easier to reason about and debug.

---

## Extending Tenancy

### Adding a custom domain to an existing tenant

```python
from apps.tenants.models import Domain, Tenant

tenant = Tenant.objects.get(schema_name="acme")
Domain.objects.create(tenant=tenant, domain="acme.example.com", is_primary=False)
```

### Enforcing tenant scope on a queryset

Views that return tenant-scoped data should always filter by `request.tenant`:

```python
def get(self, request):
    qs = MyModel.objects.filter(tenant=request.tenant)
    ...
```

Use a base mixin to avoid repeating this:

```python
class TenantScopedMixin:
    def get_queryset(self):
        return super().get_queryset().filter(tenant=self.request.tenant)
```
