# Django SaaS Kit

Production-ready Django SaaS starter with Docker, GitHub Actions CI, PostgreSQL, Redis, and Celery.

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up -d --build
```

API: http://localhost:8000/health/

**Swagger UI:** http://localhost:8000/api/docs/  
**ReDoc:** http://localhost:8000/api/redoc/  
**OpenAPI schema:** http://localhost:8000/api/schema/

Use **Authorize** in Swagger UI with `Bearer <access_token>` from `POST /api/auth/token/`.

## Local development (without Docker)

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
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
