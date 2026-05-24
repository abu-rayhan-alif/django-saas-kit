# Feature Flags

**Story:** SAAS-903 | **Layer:** L2

Django SaaS Kit uses **[django-waffle](https://waffle.readthedocs.io/)** for
feature flags.  Waffle gives you three primitives — *Flags*, *Switches*, and
*Samples* — all manageable from the Django admin without redeployment.

---

## Quick-start

### 1. Installation (already done)

`django-waffle` is in `requirements/base.txt`.  Settings are wired in
`config/settings/base.py`:

```python
# INSTALLED_APPS
THIRD_PARTY_APPS = [
    ...
    "waffle",
]

# MIDDLEWARE — must come after SessionMiddleware
MIDDLEWARE = [
    ...
    "django.contrib.sessions.middleware.SessionMiddleware",
    "waffle.middleware.WaffleMiddleware",   # ← waffle reads cookies here
    "django.middleware.common.CommonMiddleware",
    ...
]
```

### 2. Run migrations

```bash
python manage.py migrate
```

This applies waffle's schema migrations **and** the
`common/0002_feature_flags` data migration that creates the built-in flags.

---

## Flag types

| Type | Use when | Admin path |
|------|----------|------------|
| **Flag** | Per-user / per-group / percentage rollout | `/admin/waffle/flag/` |
| **Switch** | Global on/off — no request needed | `/admin/waffle/switch/` |
| **Sample** | Random percentage of *requests* | `/admin/waffle/sample/` |

---

## Checking flags in code

### In a DRF view (Flag)

```python
import waffle
from rest_framework.views import APIView
from rest_framework.response import Response

class DashboardView(APIView):
    def get(self, request):
        if waffle.flag_is_active(request, "new_dashboard"):
            return Response({"layout": "new_dashboard"})
        return Response({"layout": "classic"})
```

> `flag_is_active` requires a `request` object so waffle can evaluate
> per-user and per-group rules.

### In a service / background task (Switch)

```python
import waffle

def process_export(data):
    if waffle.switch_is_active("async_export"):
        export_task.delay(data)   # Celery path
    else:
        export_sync(data)         # synchronous fallback
```

### Percentage rollout (Sample)

```python
import waffle

def maybe_run_experiment():
    if waffle.sample_is_active("checkout_experiment"):
        run_variant_b()
    else:
        run_control()
```

### In a Django template

```django
{% load waffle_tags %}

{% flag "new_dashboard" %}
  <p>New dashboard UI is active for you.</p>
{% else %}
  <p>Classic dashboard.</p>
{% endflag %}
```

Full usage examples live in `examples/feature_flags.py`.

---

## Built-in flags

| Name | Default | Purpose |
|------|---------|---------|
| `new_dashboard` | **off** (`everyone=None`) | Example flag — ships off; toggle in admin to roll out a new UI |

---

## Admin toggle walkthrough

1. Start the dev server: `python manage.py runserver`
2. Log in as a superuser at `http://localhost:8000/admin/`
3. Navigate to **Waffle → Flags → new_dashboard**
4. Set **Everyone** to ✓ (Yes) to enable for all users, or leave as
   *Unknown* and add specific **Users** or **Groups**
5. Click **Save** — the flag takes effect on the next request (no restart needed)

> Waffle caches flag state per-request using a cookie.  The cookie name
> defaults to `dwf_<flag_name>`.  Clear it if you see stale behaviour.

---

## Testing flags

Override flag state in tests with the `waffle_flag` pytest fixture provided by
`pytest-waffle`, or patch directly:

```python
# Option A — patch the flag check
from unittest.mock import patch

def test_new_dashboard_on(client, user):
    with patch("waffle.flag_is_active", return_value=True):
        resp = client.get("/api/v1/dashboard/")
    assert resp.data["layout"] == "new_dashboard"


# Option B — use waffle's own test helpers
from waffle.testutils import override_flag

@override_flag("new_dashboard", active=True)
def test_new_dashboard_flag_on(client):
    resp = client.get("/api/v1/dashboard/")
    assert resp.status_code == 200
```

> `waffle.testutils.override_flag` / `override_switch` / `override_sample`
> are the canonical helpers — they work as decorators or context managers.

---

## Creating a new flag

### Option A — data migration (recommended for flags that ship with the code)

```python
# apps/common/migrations/0003_my_flag.py
from django.db import migrations

def create_flags(apps, schema_editor):
    Flag = apps.get_model("waffle", "Flag")
    Flag.objects.get_or_create(
        name="my_new_feature",
        defaults={"everyone": None, "note": "Describe what this flag gates."},
    )

class Migration(migrations.Migration):
    dependencies = [
        ("waffle", "0004_update_everyone_nullbooleanfield"),
        ("common", "0002_feature_flags"),
    ]
    operations = [migrations.RunPython(create_flags, migrations.RunPython.noop)]
```

### Option B — management command / seed script

```python
from waffle.models import Flag
Flag.objects.get_or_create(name="my_new_feature", defaults={"everyone": False})
```

### Option C — admin (ephemeral / per-environment)

Create from `/admin/waffle/flag/add/` directly.  Not version-controlled —
suitable for short-lived experiments.

---

## Production considerations

- **Default safe**: all flags default to `everyone=None` (off).  A missing
  flag is treated as *inactive* — it never accidentally enables unreleased
  code.
- **Cache**: waffle caches flag evaluations in Django's cache backend.  In
  production the Redis cache is used; flag changes propagate as soon as the
  cache TTL expires (default 30 s) or when the cache entry is invalidated.
- **Audit**: flag changes in the admin are recorded in Django's built-in
  `LogEntry` table.
- **Clean up**: delete flags from the admin (and remove the corresponding
  data migration) once a rollout is complete and the old code path is
  removed.
