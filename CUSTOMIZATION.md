# Customization guide (SAAS-B04)

This boilerplate marks the main extension points with `TODO` comments. Use this map
to find **where** to change things when you fork or template the repo.

## Quick reference

| What you want to change | Where to look |
|-------------------------|---------------|
| Business rules & workflows | `services/*/*_service.py` — search `# TODO: Add your business logic here` |
| Transactional emails | `apps/authentication/templates/emails/` — search `# TODO: Customize email template` |
| Tenant roles & hierarchy | `apps/rbac/models.py` — search `# TODO: Add your app-specific roles` |
| Environment & secrets | `.env` (from `.env.example`), `config/settings/` |
| HTTP routes & API surface | `config/urls.py`, `apps/*/urls.py`, `apps/*/views.py` |
| New Django app | [docs/how-to/add-new-app.md](docs/how-to/add-new-app.md) |
| New RBAC role | [docs/how-to/add-new-role.md](docs/how-to/add-new-role.md) |
| Background jobs | [docs/how-to/add-new-celery-task.md](docs/how-to/add-new-celery-task.md) |
| Demo / seed data | `examples/demo_config.py`, `services/demo/seed_service.py` |

---

## 1. Business logic (`services/`)

All domain workflows belong in **`services/`**, not in views or serializers.

| Module | File | Typical customizations |
|--------|------|------------------------|
| Users | `services/users/user_service.py` | Registration fields, profile updates, invites |
| Auth | `services/auth/auth_service.py` | Session checks, SSO hooks |
| Password reset | `services/auth/password_reset_service.py` | Token TTL, extra validation, audit logging |
| Tenants | `services/tenants/tenant_service.py` | Tenant creation, slug rules, plans |
| RBAC | `services/rbac/rbac_service.py` | Custom permission checks beyond roles |
| Demo seed | `services/demo/seed_service.py` | Local/staging fixtures (remove in production) |

Each service class includes:

```python
# TODO: Add your business logic here
```

Add methods next to existing ones. Keep views thin — they should only validate HTTP
input, call the service, and map exceptions to status codes.
See [Service layer architecture](docs/architecture/service-layer.md).

---

## 2. Email templates

Password-reset mail is rendered from:

| File | Format |
|------|--------|
| `apps/authentication/templates/emails/password_reset.txt` | Plain text |
| `apps/authentication/templates/emails/password_reset.html` | HTML |

Both files start with:

```django
{# TODO: Customize email template #}
```

**Template context** (from `PasswordResetService.request_reset`):

| Variable | Description |
|----------|-------------|
| `user_name` | Display name or username |
| `reset_link` | Frontend URL with `uid` and `token` query params |
| `uid` | Base64 user id for API confirm |
| `token` | One-time reset token |
| `hours_valid` | Link lifetime in hours |

**Related settings** (`.env` / `config/settings/base.py`):

- `EMAIL_BACKEND`, `DEFAULT_FROM_EMAIL` — delivery
- `FRONTEND_URL` — link prefix in reset emails
- `PASSWORD_RESET_TIMEOUT` — token lifetime (seconds)

For SMTP in production, see commented variables in [`.env.example`](.env.example).

---

## 3. RBAC roles

Default roles: `owner`, `admin`, `member`.

Edit **`apps/rbac/models.py`**:

```python
# TODO: Add your app-specific roles
class RoleChoices(models.TextChoices):
    ...
```

Also update `ROLE_HIERARCHY` in the same file when you need privilege ordering.

Then:

1. `python manage.py makemigrations rbac && python manage.py migrate`
2. Set `required_roles` on views using `HasRolePermission`
3. See [How to add a new RBAC role](docs/how-to/add-new-role.md)

`RBACService.VALID_ROLES` reads from `RoleChoices` automatically.

---

## 4. API & apps

| Layer | Location |
|-------|----------|
| Register apps | `LOCAL_APPS` in `config/settings/base.py` |
| Mount URLs | `config/urls.py` under `api/v1/` |
| DRF views | `apps/<app>/views.py` |
| OpenAPI tags | `@extend_schema(tags=[...])` on views |
| Serializers | `apps/<app>/serializers.py` |

---

## 5. Configuration by environment

| File | Use |
|------|-----|
| `config/settings/local.py` | Development |
| `config/settings/staging.py` | Staging |
| `config/settings/prod.py` | Production (`DEBUG=False`, SSL, etc.) |
| `config/env.py` | Loading variables from `.env` |

Copy [`.env.example`](.env.example) → `.env` before first run.

---

## 6. What not to customize blindly

| Item | Note |
|------|------|
| `config/celery.py` | Worker entrypoint; add tasks in `apps/*/tasks.py` |
| `.github/workflows/ci.yml` | CI pipeline — adjust if you add apps or coverage paths |
| `examples/demo_config.py` | Stable UUIDs for Swagger; change only if you update OpenAPI examples |

---

## 7. Further reading

- [README — Extending the boilerplate](README.md#extending-the-boilerplate)
- [Try it yourself (demo seed)](README.md#try-it-yourself)
- [Contributing](CONTRIBUTING.md)
