# Django SaaS Kit

[![CI](https://github.com/abu-rayhan-alif/django-saas-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/abu-rayhan-alif/django-saas-kit/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![codecov](https://codecov.io/gh/abu-rayhan-alif/django-saas-kit/graph/badge.svg)](https://codecov.io/gh/abu-rayhan-alif/django-saas-kit)

Production-ready Django SaaS starter with Docker, GitHub Actions CI, PostgreSQL, Redis, and Celery.

## Features

- Multi-app layout: authentication, tenants, RBAC, notifications
- JWT auth (SimpleJWT) + OpenAPI / **Swagger UI**
- Docker Compose (dev & production) with Celery workers
- GitHub Actions: lint, test, Docker build

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up -d --build
```

| Endpoint | URL |
|----------|-----|
| Health | http://localhost:8000/health/ |
| Swagger UI | http://localhost:8000/api/docs/ |
| ReDoc | http://localhost:8000/api/redoc/ |

Use **Authorize** in Swagger with `Bearer <access_token>` from `POST /api/auth/token/`.

## Local development (without Docker)

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements/local.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

## Production (Docker)

```bash
cp .env.example .env
# Set DEBUG=False, SECRET_KEY, ALLOWED_HOSTS, SECURE_SSL_REDIRECT=True behind HTTPS
docker compose -f docker-compose.prod.yml up -d --build
```

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR to `main` and `develop`:

1. **Lint** — ruff + mypy
2. **Test** — pytest with PostgreSQL & Redis service containers
3. **Build** — Docker image build (`infra/docker/Dockerfile`, `runtime` target)

## Makefile

| Command | Description |
|---------|-------------|
| `make up` | Start dev stack |
| `make down` | Stop dev stack |
| `make test` | Run pytest |
| `make lint` | Run linters |

## Architecture

Business logic lives in the **`services/`** layer; views only handle HTTP.
See [Service layer guide](docs/architecture/service-layer.md).

## Configuration

Settings are split by environment (`local`, `staging`, `prod`). Environment variables
are loaded with **[python-decouple](https://pypi.org/project/python-decouple/)**
via `config/env.py`. Copy `.env.example` to `.env` before running the app.

See [ADR-005](docs/adr/005-django-environ-vs-python-decouple.md) for the decision record.

## Contributing

We welcome contributions. Please read:

- [Contributing guide](CONTRIBUTING.md)
- [Code of conduct](CODE_OF_CONDUCT.md)
- [Pull request template](.github/PULL_REQUEST_TEMPLATE.md)

## License

This project is licensed under the **[MIT License](LICENSE)** — see the file for details.

Copyright (c) 2026 Abu Rayhan Alif
