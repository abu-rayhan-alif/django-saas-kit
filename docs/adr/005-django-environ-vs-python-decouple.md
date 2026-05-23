# ADR-005: django-environ vs python-decouple

**Status:** Accepted  
**Date:** 2026-05-22  
**Story:** SAAS-101 / SAAS-101b  
**Labels:** layer-1-mvp, architecture

## Context

Django SaaS Kit loads configuration from environment variables and a `.env` file.
We need:

- Clear **required vs optional** variables
- **Fail-fast** startup when required values are missing
- Environment-specific settings (`local`, `staging`, `prod`)
- Minimal magic and easy onboarding for contributors

Two popular libraries were evaluated:

| Library | Role |
|---------|------|
| [django-environ](https://github.com/joke2k/django-environ) | Django-focused `Env` helper with typed casts and `env.db()` |
| [python-decouple](https://github.com/HBNetwork/python-decouple) | Framework-agnostic config from `.env` + `os.environ` |

## Decision

Use **python-decouple** for all environment access, centralized in `config/env.py`,
with **dj-database-url** to parse `DATABASE_URL`.

`django-environ` is **removed** from dependencies.

## Rationale

### Why python-decouple

1. **Explicit required variables** — calling `config('SECRET_KEY')` without a default
   raises `UndefinedValueError` immediately; we wrap this in `validate_required_settings()`
   for a single clear error message at startup.
2. **Framework-agnostic** — settings logic stays in our code, not tied to Django-specific
   `environ.Env` patterns; easier to reuse validation in scripts or Celery bootstraps.
3. **Simple mental model** — `.env` file + environment variables, documented in
   `.env.example` with `[REQUIRED]` / `[OPTIONAL]` markers.
4. **Mature and lightweight** — widely used, few transitive dependencies.

### Why not django-environ

1. **Django coupling** — convenient `env.db()` and casts, but blurs “env layer” with
   Django settings modules; harder to test env validation in isolation.
2. **Inconsistent failure modes** — missing keys may surface deep inside Django setup
   (e.g. mypy plugin loading settings) rather than at a dedicated validation step.
3. **Overlap** — most features we need (bool/int/csv, `.env` read) are covered by
   decouple + `dj-database-url` with less surface area.

## Consequences

### Positive

- `config/env.py` is the single source of truth for env access and validation.
- `.env.example` documents every variable with required/optional labels.
- CI and local dev share the same contract; missing `SECRET_KEY` fails before requests.

### Negative / mitigations

- No built-in `env.db()` — mitigated by `dj-database-url` in `get_database_url_config()`.
- Cast helpers differ from django-environ API — mitigated by thin wrappers (`get_str`,
  `get_bool`, `get_int`, `get_csv`) in `config/env.py`.

## Implementation notes

```
config/
  env.py              # decouple + validation
  settings/
    base.py           # shared settings, calls validate_required_settings()
    local.py          # dev overrides
    staging.py        # staging overrides (extends prod)
    prod.py           # hardened production
    mypy.py           # type-checking only (sets os.environ before base import)
```

**Required variables (all environments using `base`):**

- `SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`

**Additional production constraints:**

- `ALLOWED_HOSTS` must be non-empty in `prod` and `staging`

## References

- [python-decouple documentation](https://pypi.org/project/python-decouple/)
- [dj-database-url](https://github.com/jazzband/dj-database-url)
- Story SAAS-101 acceptance criteria
