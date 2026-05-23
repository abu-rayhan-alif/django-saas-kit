# Contributing to Django SaaS Kit

Thank you for your interest in contributing. This project is an open-source Django
SaaS starter — issues, docs, and PRs are welcome.

## Code of conduct

Please read and follow our [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE) used by this project.

## Ticket flow

Work is tracked in two places depending on visibility:

| Stage | Where | Who |
|-------|--------|-----|
| **Private planning** | Personal **Jira** (or your own backlog) | Maintainers / you — spikes, internal notes, client-specific ideas |
| **Public execution** | **GitHub Issues** + [Project board](docs/setup/github-project.md) | Everyone — bugs, features, and merged work |

**Flow:**

1. **Ideate** — capture rough ideas in personal Jira (optional).
2. **Publish** — when ready for community visibility, open a [bug report](.github/ISSUE_TEMPLATE/bug_report.yml) or [feature request](.github/ISSUE_TEMPLATE/feature_request.yml) on GitHub.
3. **Triage** — maintainers label (`adr`, `security`, `testing`, `gdpr`, `docs`, …) and move the card on the project board: **Backlog → In Progress → In Review → Done**.
4. **Implement** — fork, branch, PR using the [pull request template](.github/PULL_REQUEST_TEMPLATE.md).
5. **Release** — changelog + tag per [docs/VERSIONING.md](docs/VERSIONING.md).

Do **not** open public issues for **security** findings — use [SECURITY.md](SECURITY.md) (label: `security`).

### GitHub labels

| Label | Use for |
|-------|---------|
| `adr` | Architecture Decision Records in `docs/adr/` |
| `security` | Vulnerabilities or hardening (usually via private advisory) |
| `testing` | Tests, coverage, CI |
| `gdpr` | Privacy, personal data, compliance |
| `docs` | Documentation-only changes |

Labels are defined in [`.github/labels.yml`](.github/labels.yml) and synced by the **Sync GitHub labels** workflow.

## Getting started

### Using this repository as a template

See [Start from this template](README.md#start-from-this-template) in the README.

Maintainers: [Template setup checklist](docs/setup/template-repository.md).

### Prerequisites

- Python **3.12+**
- Docker & Docker Compose (recommended)
- Git

### Quickstart

```bash
git clone https://github.com/abu-rayhan-alif/django-saas-kit.git
cd django-saas-kit
make dev
```

API docs: http://localhost:8000/api/docs/

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

### Environment variables

Copy `.env.example` to `.env`. **Required** variables (`SECRET_KEY`, `DATABASE_URL`,
`REDIS_URL`) must be set or Django will fail at startup. See
[ADR-005](docs/adr/005-django-environ-vs-python-decouple.md).

## Versioning and releases

- **Semantic Versioning** — [docs/VERSIONING.md](docs/VERSIONING.md)
- **Changelog** — [CHANGELOG.md](CHANGELOG.md) ([Keep a Changelog](https://keepachangelog.com/))

## Development workflow

1. Fork the repository and create a branch from `main` or `develop`.
2. Make your changes with clear, focused commits.
3. Run quality checks before opening a PR:

```bash
make lint          # ruff + mypy
make test          # pytest
```

4. Open a pull request — complete every item in the [PR checklist](.github/PULL_REQUEST_TEMPLATE.md):
   - Tests passed
   - Linted
   - ADR updated (if architecture changes)
   - Docs updated
   - Breaking change noted (if applicable)

## Code style

| Tool | Purpose |
|------|---------|
| [Ruff](https://docs.astral.sh/ruff/) | Linting & formatting |
| [mypy](https://mypy.readthedocs.io/) | Static type checking (django-stubs) |
| [pytest](https://docs.pytest.org/) | Tests |

Configuration: `pyproject.toml`. Business logic belongs in `services/` — see
[Service layer guide](docs/architecture/service-layer.md).

## Testing

- Tests live under `tests/`.
- CI enforces **80%** coverage on `config` and `services`.

```bash
pytest -v
pytest --cov=config --cov=services --cov-fail-under=80
```

## Reporting issues

| Type | Where |
|------|--------|
| Bug | [Bug report template](.github/ISSUE_TEMPLATE/bug_report.yml) |
| Feature | [Feature request template](.github/ISSUE_TEMPLATE/feature_request.yml) |
| Security | [SECURITY.md](SECURITY.md) — private advisory only |

## Project structure

```
apps/           # Django apps
config/         # Settings, URLs, Celery
services/       # Domain service layer
docs/           # ADRs, how-to, setup guides
tests/          # Pytest suite
```

## Governance files

| File | Purpose |
|------|---------|
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Contributor Covenant |
| [LICENSE](LICENSE) | MIT |
| [SECURITY.md](SECURITY.md) | Vulnerability reporting |
| [CUSTOMIZATION.md](CUSTOMIZATION.md) | Extension points |

## Questions?

Open a [feature request](.github/ISSUE_TEMPLATE/feature_request.yml) or a GitHub Discussion if enabled.
