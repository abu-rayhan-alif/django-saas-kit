<div align="center">

```
██████╗      ██╗ █████╗ ███╗   ██╗ ██████╗  ██████╗
██╔══██╗     ██║██╔══██╗████╗  ██║██╔════╝ ██╔═══██╗
██║  ██║     ██║███████║██╔██╗ ██║██║  ███╗██║   ██║
██║  ██║██   ██║██╔══██║██║╚██╗██║██║   ██║██║   ██║
██████╔╝╚█████╔╝██║  ██║██║ ╚████║╚██████╔╝╚██████╔╝
╚═════╝  ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝
                   S a a S   K i t
```

**Ship your multi-tenant SaaS product in days, not months.**

[![CI](https://github.com/abu-rayhan-alif/django-saas-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/abu-rayhan-alif/django-saas-kit/actions/workflows/ci.yml)
[![codecov](https://img.shields.io/codecov/c/github/abu-rayhan-alif/django-saas-kit?logo=codecov&logoColor=white)](https://codecov.io/gh/abu-rayhan-alif/django-saas-kit)
[![Python](https://img.shields.io/badge/python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-5.x-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-FAB040?logo=pre-commit&logoColor=black)](https://pre-commit.com/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)

[**Live Docs →**](http://localhost:8000/api/docs/) · [**ADRs**](docs/adr/) · [**Architecture**](docs/architecture/) · [**Contributing**](CONTRIBUTING.md)

</div>

---

## What is this?

Django SaaS Kit is a **production-ready backend template** for teams who want to skip the boilerplate and start building features on day one.

It gives you the hard parts out of the box — multi-tenant routing, JWT auth with rotation, RBAC, async tasks, real-time notifications, GDPR tooling, structured logging — all wired together and tested.

```
Your idea  ──►  clone  ──►  make dev  ──►  ship features
              (5 sec)    (2 min)      (today)
```

---

## 60-Second Quickstart

> **Requires:** Docker + Docker Compose (Docker Desktop includes both)

```bash
# 1. Clone
git clone https://github.com/abu-rayhan-alif/django-saas-kit.git
cd django-saas-kit

# 2. Boot the full stack (DB + Redis + Celery + web)
make dev

# 3. Open the interactive API docs
open http://localhost:8000/api/docs/
```

`make dev` handles everything: copies `.env`, builds images, runs migrations, starts all services.

**No `make`?**
```bash
cp .env.example .env && docker compose up -d --build
```

<details>
<summary><strong>Without Docker (virtualenv)</strong></summary>

```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

pip install -r requirements/local.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

</details>

### What's running

| Service | URL | Notes |
|---------|-----|-------|
| **Swagger UI** | [localhost:8000/api/docs/](http://localhost:8000/api/docs/) | Try every endpoint interactively |
| ReDoc | [localhost:8000/api/redoc/](http://localhost:8000/api/redoc/) | Clean reference view |
| Health | [localhost:8000/health/](http://localhost:8000/health/) | Load-balancer probe |
| Admin | [localhost:8000/admin/](http://localhost:8000/admin/) | Django admin |

---

## Feature Overview

<table>
<tr>
<td width="50%" valign="top">

### Auth & Identity
- JWT access tokens (15 min) + rotating refresh tokens (7 days)
- Token blacklist on logout
- **Social OAuth** — Google & GitHub login (`POST /auth/social/`)
- **Two-Factor Auth (TOTP)** — Google Authenticator / Authy compatible
- Self-service password reset via email
- Login rate limiting (5/min default)

### Multi-Tenancy
- Subdomain routing — `tenant1.localhost` → `request.tenant`
- `Domain` model for multi-domain support
- `TenantService.create_tenant()` — atomic setup
- 404 / 403 for unknown / inactive tenants

### RBAC
- Tenant-scoped roles: `owner › admin › member`
- Permission checks in one decorator
- Role assignment + revocation endpoints

### User Profiles
- Extended profile: avatar upload, bio, phone, timezone
- `GET /users/me/` returns user + profile + 2FA status in one call
- `PATCH /users/me/profile/` for partial updates

</td>
<td width="50%" valign="top">

### Billing (Stripe)
- Plan model with member + storage limits
- Subscription lifecycle: trialing → active → past\_due → canceled
- Grace period during dunning
- Stripe webhook processing (idempotent, Celery-backed)

### Platform
- Celery workers + Beat scheduler (Redis broker)
- Django Channels — real-time WebSocket notifications
- **Feature flags** — per-tenant overrides on top of `django-waffle`
- **Plan-based rate limiting** — `TenantPlanThrottle` per subscription tier
- Structured JSON logs (structlog) with request + trace IDs

### Developer Experience
- OpenAPI schema auto-generated (`drf-spectacular`)
- Consistent error envelope: `{error, message, details}`
- Cursor + page-number pagination
- `select_related` / `prefetch_related` patterns enforced

### Compliance
- Sensitive-field log redaction (password, token, email)
- GDPR right-to-erasure management command
- `docs/gdpr.md` policy + FK handling table

</td>
</tr>
</table>

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        HTTP Request                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
              ┌─────────────▼─────────────┐
              │       MIDDLEWARE STACK     │
              │  SecurityMiddleware        │
              │  RequestContextMiddleware  │  ← binds request_id
              │  TenantMiddleware          │  ← resolves tenant
              │  AuthenticationMiddleware  │  ← verifies JWT
              └─────────────┬─────────────┘
                            │
              ┌─────────────▼─────────────┐
              │     VIEW  (thin adapter)   │
              │  validate input            │
              │  call service              │
              │  map result → HTTP         │
              └─────────────┬─────────────┘
                            │
              ┌─────────────▼─────────────┐
              │   SERVICE LAYER (no HTTP) │
              │  business rules            │
              │  validation                │
              │  orchestration             │
              └─────────────┬─────────────┘
                            │
              ┌─────────────▼─────────────┐
              │   MODELS / POSTGRES        │
              │  UUID PKs, soft delete     │
              │  audit fields              │
              └────────────────────────────┘
```

| Layer | Location | Rule |
|-------|----------|------|
| Views / serializers | `apps/*/views.py` | HTTP only — no business logic |
| Services | `services/` | No HTTP imports |
| Models | `apps/*/models.py` | Schema + DB constraints |
| RBAC | `apps/rbac/` | Tenant-scoped role checks |

→ Full design: [docs/architecture/service-layer.md](docs/architecture/service-layer.md)

---

## Project Structure

```
django-saas-kit/
├── apps/
│   ├── authentication/     # JWT, password reset, registration, OAuth, 2FA
│   ├── billing/            # Stripe plans, subscriptions, webhook handler
│   ├── common/             # Pagination, exceptions, middleware, throttling
│   ├── features/           # Per-tenant feature flags (waffle + overrides)
│   ├── invitations/        # Token-based team invitations
│   ├── notifications/      # WebSocket + DB notifications
│   ├── audit/              # Immutable audit log
│   ├── rbac/               # Roles, permissions
│   ├── tenants/            # Tenant model, Domain model, middleware
│   └── users/              # User profile, avatar, tasks
│
├── services/               # Pure business logic (no HTTP)
│   ├── auth/               # Password reset, social auth service
│   ├── features/           # FeatureService — flag resolution
│   ├── notifications/      # Notification service
│   ├── rbac/               # RBAC service
│   ├── tenants/            # TenantService.create_tenant()
│   └── users/              # UserService, GDPRService
│
├── config/
│   ├── settings/
│   │   ├── base.py         # Shared settings
│   │   ├── local.py        # Dev overrides
│   │   └── prod.py         # Production
│   ├── urls.py
│   └── celery.py
│
├── tests/
│   ├── unit/               # Fast, no-DB tests
│   └── integration/        # Full-stack endpoint tests
│
└── docs/
    ├── adr/                # Architecture decision records
    ├── architecture/       # Design docs
    └── gdpr.md             # Privacy & compliance
```

---

## API Reference

All endpoints live under `/api/v1/`. Authenticate with `Authorization: Bearer <access_token>`.

| Resource | Base path | Key endpoints |
|----------|-----------|---------------|
| **Auth** | `/api/v1/auth/` | `POST /token/` · `POST /register/` · `POST /social/` |
| **2FA** | `/api/v1/auth/2fa/` | `GET /setup/` · `POST /enable/` · `POST /complete/` |
| **Users** | `/api/v1/users/` | `GET /me/` · `PATCH /me/profile/` |
| **Tenants** | `/api/v1/tenants/` | `GET /` · `POST /` |
| **RBAC** | `/api/v1/rbac/<tenant_id>/` | `GET /roles/` · `POST /roles/assign/` |
| **Notifications** | `/api/v1/notifications/` | `GET /` · `PATCH /<id>/read/` |
| **Billing** | `/api/v1/billing/` | `POST /webhook/` |
| **Features** | `/api/v1/features/` | `GET /` · `GET /<flag_name>/` |

**Get a token in 3 lines:**
```bash
curl -s -X POST http://tenant1.localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yourpassword"}' | jq .access
```

**Social login (Google / GitHub):**
```bash
curl -s -X POST http://tenant1.localhost:8000/api/v1/auth/social/ \
  -H "Content-Type: application/json" \
  -d '{"provider": "google", "access_token": "<oauth_token>"}'
```

→ Full interactive docs: [localhost:8000/api/docs/](http://localhost:8000/api/docs/)

---

## Two-Factor Authentication

Enable TOTP 2FA for any user account (Google Authenticator, Authy, etc.):

```bash
# 1. Get setup QR code (authenticated)
GET /api/v1/auth/2fa/setup/
# → returns secret + provisioning_uri + qr_svg

# 2. Scan QR in your authenticator app, then verify the first code
POST /api/v1/auth/2fa/enable/    {"code": "123456"}
# → returns backup_codes (save these!)

# 3. On next login, if 2FA is enabled the token endpoint returns:
#    {"two_fa_required": true, "session_key": "..."}
# Complete login with:
POST /api/v1/auth/2fa/complete/  {"session_key": "...", "code": "123456"}
# → returns normal JWT pair
```

---

## Social OAuth

The OAuth flow is frontend-initiated — your client handles the redirect and callback, then hands the access token to the API:

```
User clicks "Login with Google"
    → Frontend redirects to Google OAuth consent
    → Google redirects back with code
    → Frontend exchanges code for access_token
    → POST /api/v1/auth/social/ {"provider":"google","access_token":"..."}
    → API returns JWT pair (creates account on first login)
```

Supported providers: `google`, `github`.

---

## Feature Flags

Feature flags combine global `django-waffle` switches with per-tenant overrides:

```python
from services.features import FeatureService

# In a view — reads tenant from request automatically
if FeatureService.is_enabled("advanced_analytics", request=request):
    ...

# In a service / task
if FeatureService.is_enabled("bulk_export", tenant=tenant):
    ...

# Check all flags at once (used by the frontend)
# GET /api/v1/features/
# → {"advanced_analytics": true, "bulk_export": false, ...}
```

Per-plan flags are configured in settings and synced automatically on subscription changes:

```python
# config/settings/base.py
PLAN_FEATURE_FLAGS = {
    "free":       {"api_access": False, "advanced_analytics": False},
    "starter":    {"api_access": True,  "advanced_analytics": False},
    "pro":        {"api_access": True,  "advanced_analytics": True},
    "enterprise": {"api_access": True,  "advanced_analytics": True, "sso": True},
}
```

Admin overrides live in Django Admin under **Tenant Feature Flags**.

---

## Plan-Based Rate Limiting

Add `TenantPlanThrottle` to any view to enforce subscription-tier rate limits:

```python
from apps.common.throttling import TenantPlanThrottle

class MyView(APIView):
    throttle_classes = [TenantPlanThrottle]
```

---

## Multi-Tenancy Setup

Subdomains route requests to the correct tenant automatically.

**1. Add hosts (one-time)**

```
# /etc/hosts  (Linux/macOS)
# C:\Windows\System32\drivers\etc\hosts  (Windows)

127.0.0.1   tenant1.localhost
127.0.0.1   tenant2.localhost
```

**2. Create tenants**

```python
# python manage.py shell
from services.tenants import TenantService

TenantService.create_tenant("Acme Corp",  "acme",  "acme.localhost")
TenantService.create_tenant("Beta Ltd",   "beta",  "beta.localhost")
```

**3. Make requests**

```bash
# Hits Acme's workspace
curl http://acme.localhost:8000/api/v1/auth/token/ ...

# Hits Beta's workspace
curl http://beta.localhost:8000/api/v1/auth/token/ ...
```

→ Architecture explained: [docs/architecture/tenancy.md](docs/architecture/tenancy.md)

---

## Environment Variables

```bash
cp .env.example .env   # then edit as needed
```

| Variable | Required | Default | Purpose |
|----------|:--------:|---------|---------|
| `SECRET_KEY` | **Yes** | — | Django signing key |
| `DATABASE_URL` | **Yes** | `postgres://...@db:5432/saas_db` | PostgreSQL |
| `REDIS_URL` | **Yes** | `redis://redis:6379/0` | Cache + Celery |
| `DEBUG` | | `False` | Dev mode |
| `ALLOWED_HOSTS` | Prod | — | Comma-separated hostnames |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | | `15` | Access token TTL |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | | `7` | Refresh token TTL |
| `EMAIL_BACKEND` | | `console` | Swap for SMTP in prod |
| `DEFAULT_FROM_EMAIL` | | `noreply@example.com` | From address |
| `FRONTEND_URL` | | `http://localhost:3000` | Password-reset & billing links |
| `BILLING_PORTAL_URL` | | `$FRONTEND_URL/billing` | Billing email CTA |
| `SITE_NAME` | | `Django SaaS Kit` | Email branding |
| `STRIPE_SECRET_KEY` | Billing | — | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | Billing | — | Webhook signature verification |
| `THROTTLE_PLAN_FREE` | | `60/minute` | Rate limit for free plan |
| `THROTTLE_PLAN_STARTER` | | `300/minute` | Rate limit for starter plan |
| `THROTTLE_PLAN_PRO` | | `1000/minute` | Rate limit for pro plan |
| `THROTTLE_PLAN_ENTERPRISE` | | `10000/minute` | Rate limit for enterprise plan |
| `SENTRY_DSN` | Prod | — | Error tracking |

---

## Common Commands

```bash
# Development
make dev          # first-time setup (copy .env + build + start)
make up           # start stack
make down         # stop stack
make logs         # tail web logs
make shell        # Django shell inside container

# Code quality
make lint         # ruff + mypy
make format       # ruff format + auto-fix
make test         # pytest (no Docker needed)

# Database
make migrate      # run migrations
docker compose exec web python manage.py seed_demo    # seed demo data
docker compose exec web python manage.py check_redis  # verify Redis

# GDPR
docker compose exec web python manage.py delete_user_data <user_id>
docker compose exec web python manage.py delete_user_data <user_id> --hard-delete
```

---

## GDPR — Right to be Forgotten

Erase a user's personal data in one command:

```bash
# Anonymize (default) — wipes PII, keeps row for audit integrity
docker compose exec web python manage.py delete_user_data <user_id>

# Hard-delete — removes the row entirely
docker compose exec web python manage.py delete_user_data <user_id> --hard-delete

# Scripted (no prompt)
docker compose exec web python manage.py delete_user_data <user_id> --no-input
```

What gets erased: username · email · name · password · profile · all notifications · all roles · all JWT tokens.

→ Policy + FK table: [docs/gdpr.md](docs/gdpr.md)

---

## Stack

| Layer | Technology |
|-------|-----------|
| Framework | Django 5 + Django REST Framework |
| Auth | `djangorestframework-simplejwt` + `pyotp` (TOTP 2FA) |
| Social Auth | Custom OAuth token exchange (Google, GitHub) |
| Database | PostgreSQL 16 |
| Cache / Broker | Redis 7 |
| Async tasks | Celery + Celery Beat |
| Real-time | Django Channels (WebSocket) |
| API docs | `drf-spectacular` (OpenAPI 3) |
| Logging | `structlog` (JSON in prod, console in dev) |
| Feature flags | `django-waffle` + per-tenant overrides |
| Billing | Stripe (webhooks, subscriptions, dunning) |
| File storage | Local filesystem / S3-compatible (MinIO in dev) |
| Error tracking | Sentry (optional, gate with `SENTRY_DSN`) |
| Linting | `ruff` + `mypy` |
| CI | GitHub Actions |
| Containerisation | Docker + Docker Compose |

---

## CI / CD

GitHub Actions runs on every push to `main` and every PR:

```
push / PR
    │
    ├── lint      ruff check . && mypy .
    ├── test      pytest  (PostgreSQL + Redis service containers)
    └── build     docker build --target runtime
```

Configuration: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

---

## Contributing

Contributions are welcome — bug fixes, features, docs, and ADRs.

```bash
git checkout -b feature/your-feature
# make changes
make lint && make test
git push origin feature/your-feature
# open a PR
```

→ Read [CONTRIBUTING.md](CONTRIBUTING.md) and the [PR template](.github/PULL_REQUEST_TEMPLATE.md) before opening a pull request.

---

<div align="center">

**MIT License** · Copyright © 2026 [Abu Rayhan Alif](https://github.com/abu-rayhan-alif)

*If this saved you time, leave a ⭐ — it helps others find the project.*

</div>
