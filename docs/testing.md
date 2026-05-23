# Testing & coverage

**Story:** SAAS-801 | **Layer:** L1

How to run tests locally and where to find coverage reports in CI.

---

## CI pipeline

Workflow: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

| Trigger | When |
|---------|------|
| **Push** | `main`, `develop` |
| **Pull request** | Any branch (opened, updated, reopened) |
| **Manual** | Actions → CI → Run workflow |

| Job | What it runs |
|-----|----------------|
| **Lint** | `ruff check`, `ruff format --check`, `mypy` |
| **Test** | `pytest` against **PostgreSQL 16** + **Redis 7** service containers |
| **Build** | `docker build` (`infra/docker/Dockerfile`, `runtime` target) |

Status badge: [![CI](https://github.com/abu-rayhan-alif/django-saas-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/abu-rayhan-alif/django-saas-kit/actions/workflows/ci.yml) (see [README](../README.md)).

---

## Coverage gate (80%)

CI **fails** if combined coverage for `config/` + `services/` is below **80%**.

Configured in:

| File | Setting |
|------|---------|
| [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | `pytest --cov-fail-under=80` |
| [`pyproject.toml`](../pyproject.toml) | `[tool.coverage.report] fail_under = 80` |

Measured paths (`[tool.coverage.run] source`):

- `config/`
- `services/`

Excluded: migrations, `tests/`, `manage.py`.

---

## Where to see coverage reports

### 1. GitHub Actions (every CI run)

1. Open the repository on GitHub → **Actions** → select a **CI** workflow run.
2. Open the **Test** job.
3. Scroll to **Artifacts** → download **`coverage-report`**.
4. Unzip and open **`htmlcov/index.html`** in a browser for a line-by-line HTML report.
5. Use **`coverage.xml`** for SonarQube, Codecov, or other tools.

Artifacts are kept for **14 days**.

### 2. Codecov (optional, public repos)

If [Codecov](https://codecov.io/) is linked to the repo, the README [![codecov](https://codecov.io/gh/abu-rayhan-alif/django-saas-kit/graph/badge.svg)](https://codecov.io/gh/abu-rayhan-alif/django-saas-kit) badge shows the latest trend. CI uploads `coverage.xml` on each run (`fail_ci_if_error: false` so Codecov outages do not block merges).

### 3. Local terminal

```bash
# Docker stack running, or local Postgres + Redis with .env set
make test
# or
pytest --cov=config --cov=services --cov-report=term-missing --cov-fail-under=80
```

HTML report locally:

```bash
pytest --cov=config --cov=services --cov-report=html:htmlcov
# open htmlcov/index.html
```

---

## Local test setup

| Requirement | CI | Local |
|-------------|-----|-------|
| PostgreSQL | Service container | Docker Compose `db` or `DATABASE_URL` |
| Redis | Service container | Docker Compose `redis` or `REDIS_URL` |
| Env vars | Set in workflow | Copy `.env.example` → `.env` |

```bash
cp .env.example .env
make dev          # starts Postgres + Redis
make migrate
make test
```

Tests use `config.settings.local` and the `celery_eager` + `locmem_cache` fixtures in [`tests/conftest.py`](../tests/conftest.py) so Celery and cache do not require Redis for every test.

---

## Lint locally (matches CI Job 1)

```bash
make lint
# or
ruff check .
ruff format --check .
DJANGO_SETTINGS_MODULE=config.settings.mypy mypy .
```

---

## Related

- [Makefile](../Makefile) — `make test`, `make lint`
- [CONTRIBUTING.md](../CONTRIBUTING.md)
- [Background jobs](background-jobs.md)
