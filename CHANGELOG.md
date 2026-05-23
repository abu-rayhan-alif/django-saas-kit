# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

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
- Health check endpoint (`/health/`)
- `Makefile` shortcuts for Docker, migrate, test, lint, and seed

### Changed

- N/A (initial release)

### Fixed

- N/A (initial release)

### Removed

- N/A (initial release)

[Unreleased]: https://github.com/abu-rayhan-alif/django-saas-kit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/abu-rayhan-alif/django-saas-kit/releases/tag/v0.1.0
