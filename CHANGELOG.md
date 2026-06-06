# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Dependabot weekly updates for Python packages and GitHub Actions (SAAS-703)
- CI workflow documentation and coverage artifacts ([docs/testing.md](docs/testing.md)) (SAAS-801)
- Per-tenant feature flags API and `FeatureService` ([docs/feature-flags.md](docs/feature-flags.md))
- Social OAuth login (Google, GitHub) and TOTP two-factor authentication
- User profile endpoints (`GET/PATCH /users/me/profile/`)
- Billing Celery tasks for Stripe webhooks, dunning, and trial-ending emails
- Test coverage for features, billing tasks, social auth, 2FA, and user profiles

### Changed

- Align pre-commit Ruff hook with local dev (`ruff` 0.15.14)

### Fixed

- Pre-commit Ruff version mismatch causing CI format failures
- Mypy type annotations in features and billing modules

### Removed##

---

## [0.1.0] - 2026-05-23

### Added

- Multi-app Django layout: `users`, `authentication`, `tenants`, `rbac`, `notifications`, `common`
- **Service layer** (`services/`) for domain logic separate from HTTP adapters
- JWT authentication (SimpleJWT): obtain, refresh, blacklist
- User registration and password reset (email templates: text + HTML)
- Tenant-scoped **RBAC** (`owner`, `admin`, `member`) with `RBACService` and DRF permissions
- `BaseModel` with UUID primary keys, audit fields, and soft delete (`apps/common`)
- OpenAPI 3 schema, Swagger UI (`/api/docs/`), and ReDoc (`/api/redoc/`)
- API versioning under `/api/v1/`
- Docker Compose stack: web, PostgreSQL, Redis, Celery worker, Celery beat
- GitHub Actions CI: ruff, mypy, pytest (80% coverage on `config` + `services`), Docker build
- `python manage.py seed_demo` — two demo tenants and `admin@tenant1.localhost` / `password123`
- `examples/` demo config and OpenAPI request examples
- Documentation: service layer guide, how-to guides (new app, role, Celery task), `CUSTOMIZATION.md`
- GitHub template repository setup guide (`docs/setup/template-repository.md`)
- Liveness endpoint (`GET /health/`) and readiness endpoint (`GET /ready/`) (SAAS-602)
- Sentry error monitoring via `SENTRY_DSN` (SAAS-603)
- CORS (`django-cors-headers`), CSP, HSTS, and production TLS headers (SAAS-701)
- DRF rate limiting — login 5/min, authenticated API 100/min (SAAS-702)
- `Makefile` shortcuts for Docker, migrate, test, lint, and seed

### Changed

- N/A (initial release)

### Fixed

- N/A (initial release)

### Removed

- N/A (initial release)

[Unreleased]: https://github.com/abu-rayhan-alif/django-saas-kit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/abu-rayhan-alif/django-saas-kit/releases/tag/v0.1.0
