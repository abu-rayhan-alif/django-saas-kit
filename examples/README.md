# Demo data (SAAS-B02)

This folder defines **stable demo tenants and credentials** used by:

- `python manage.py seed_demo`
- Swagger / OpenAPI request examples (`openapi_examples.py`)

## Tenants

| Slug | Name | UUID |
|------|------|------|
| `tenant1` | Tenant One | `00000000-0000-4000-8000-000000000001` |
| `tenant2` | Tenant Two | `00000000-0000-4000-8000-000000000002` |

## Demo user (Tenant One admin)

| Field | Value |
|-------|--------|
| Email / username | `admin@tenant1.localhost` |
| Password | `password123` |
| Role in Tenant One | `admin` |

## Load demo data

```bash
python manage.py migrate
python manage.py seed_demo
```

Re-running the command is safe (idempotent).

Configuration lives in [`demo_config.py`](demo_config.py). Seeding logic is in [`services/demo/seed_service.py`](../services/demo/seed_service.py).
