# Contributing to Django SaaS Kit

Thank you for your interest in contributing. This project is an open-source Django
SaaS starter — issues, docs, and PRs are welcome.

## Code of conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE) used by this project.

## Getting started

### Using this repository as a template

End users: see [Start from this template](README.md#start-from-this-template) in the README.

Maintainers enabling the GitHub template: [docs/setup/template-repository.md](docs/setup/template-repository.md).

### Prerequisites

- Python **3.12+**
- Docker & Docker Compose (recommended)
- Git

### Local setup (Docker)

```bash
git clone https://github.com/abu-rayhan-alif/django-saas-kit.git
cd django-saas-kit
cp .env.example .env
docker compose up -d --build
```

### Local setup (Python venv)

```bash
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows
pip install -r requirements/local.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

API docs: http://localhost:8000/api/docs/

### Environment variables

Copy `.env.example` to `.env`. **Required** variables (`SECRET_KEY`, `DATABASE_URL`,
`REDIS_URL`) must be set or Django will fail at startup. See
[ADR-005](docs/adr/005-django-environ-vs-python-decouple.md) for rationale.

## Versioning and releases

- Version format: **Semantic Versioning** (`MAJOR.MINOR.PATCH`) — see [docs/VERSIONING.md](docs/VERSIONING.md)
- Changelog: [CHANGELOG.md](CHANGELOG.md) ([Keep a Changelog](https://keepachangelog.com/))
- Record user-facing changes under `[Unreleased]`; maintainers cut releases via git tags and GitHub Releases

## Development workflow

1. Fork the repository and create a branch from `main` or `develop`.
2. Make your changes with clear, focused commits.
3. Run quality checks before opening a PR:

```bash
make lint          # ruff + mypy
make test          # pytest
# optional
pre-commit run --all-files
```

4. Open a pull request using the [PR template](.github/PULL_REQUEST_TEMPLATE.md).

## Code style

| Tool | Purpose |
|------|---------|
| [Ruff](https://docs.astral.sh/ruff/) | Linting & formatting |
| [mypy](https://mypy.readthedocs.io/) | Static type checking (django-stubs) |
| [pytest](https://docs.pytest.org/) | Tests |

Configuration lives in `pyproject.toml`. Keep changes minimal and consistent with
existing patterns in `apps/`, `config/`, and `services/`.

## Testing

- Unit tests live under `tests/`.
- Aim to cover new logic; CI enforces **80%** coverage on `config` and `services`.
- Integration tests may use PostgreSQL and Redis (see `.github/workflows/ci.yml`).

```bash
pytest -v
pytest --cov=config --cov=services --cov-fail-under=80
```

## Reporting issues

Use GitHub issue templates:

- [Bug report](.github/ISSUE_TEMPLATE/bug_report.yml)
- [Feature request](.github/ISSUE_TEMPLATE/feature_request.yml)

Do **not** open public issues for security vulnerabilities — use
[GitHub Security Advisories](https://github.com/abu-rayhan-alif/django-saas-kit/security/policy) instead.

## Project structure

```
apps/           # Django apps (auth, tenants, rbac, …)
config/         # Settings, URLs, Celery
services/       # Domain service layer
docs/how-to/    # Extension guides (new app, role, Celery task)
infra/docker/   # Dockerfile & entrypoint
tests/          # Pytest suite
```

## Questions?

Open a [feature request](.github/ISSUE_TEMPLATE/feature_request.yml) or start a
GitHub Discussion if enabled on the repository.
