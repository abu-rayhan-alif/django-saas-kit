# Security Policy

**Responsible disclosure:** Report vulnerabilities privately via [GitHub Security Advisories](https://github.com/abu-rayhan-alif/django-saas-kit/security/advisories/new) — do not open public issues for security bugs.

---

## Threat model (Asset → Threat → Mitigation)

| Asset | Threat | Mitigation |
|-------|--------|------------|
| **User credentials** | Brute force / credential stuffing on login and registration | **Rate limiting** on auth endpoints (reverse proxy or DRF throttling in production); **strong password hashing** — configure **Argon2id** in `PASSWORD_HASHERS` (see below); Django password validators on registration; never log passwords |
| **Refresh token** | Token theft (XSS, leaked storage, network intercept) | **Short-lived access tokens** (default 15 min); **refresh rotation** (`ROTATE_REFRESH_TOKENS`); **blacklist after rotation** (`BLACKLIST_AFTER_ROTATION` + `token_blacklist` app); logout via `POST /api/v1/auth/token/blacklist/`; HTTPS only in production |
| **API endpoint** | Privilege escalation (cross-tenant or role bypass) | **Tenant-scoped RBAC** (`HasRolePermission`, `required_roles` on views); resolve tenant from URL `tenant_id` or `X-Tenant-ID`; `RBACService.has_role` — roles do not cross tenants; deny by default (`IsAuthenticated` + role checks) |
| **Auth endpoint** | Replay of captured tokens or reset links | **Token expiry** (JWT `exp` + refresh lifetime); **refresh rotation** invalidates reused refresh tokens; password-reset tokens single-use (Django `PasswordResetTokenGenerator`); optional **nonce / `jti` claim** for high-security deployments |

### Implemented in this kit (reference)

| Area | Location |
|------|----------|
| JWT lifetimes & blacklist | `config/settings/base.py` → `SIMPLE_JWT` |
| RBAC | `apps/rbac/permissions.py`, `services/rbac/` |
| Password validation | `AUTH_PASSWORD_VALIDATORS`, `UserService.create_user` |
| Private reporting | This file + [GitHub Security Advisories](https://github.com/abu-rayhan-alif/django-saas-kit/security/advisories/new) |

### Recommended production hardening

**Argon2 password hashing** (replace default PBKDF2):

```bash
pip install django[argon2]
```

```python
# config/settings/prod.py
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",  # verify old hashes until users re-login
]
```

**Rate limiting** (example for login):

```python
# config/settings/prod.py
REST_FRAMEWORK = {
    ...
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "20/minute", "user": "100/minute"},
}
```

Apply stricter scopes on `POST /api/v1/auth/token/` and registration routes.

---

## Supported versions

| Version | Supported |
|---------|-----------|
| `0.1.x` | Yes |
| `< 0.1` | No |

---

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

1. **[GitHub Security Advisories](https://github.com/abu-rayhan-alif/django-saas-kit/security/advisories/new)** (preferred — private report)
2. If Advisories are unavailable, email the maintainer via the GitHub profile with: description, impact, steps to reproduce, affected version(s), and suggested fix if any.

We aim to acknowledge reports within **72 hours** and provide a remediation timeline based on severity.

---

## Secure development

- Keep `SECRET_KEY` and database credentials out of version control (use `.env`)
- Run production with `DEBUG=False` and `SECURE_SSL_REDIRECT=True` behind HTTPS
- Review [CUSTOMIZATION.md](CUSTOMIZATION.md) before deploying forked code
- See [Background jobs](docs/background-jobs.md) for Celery retry and idempotency
- Follow the [Contributing guide](CONTRIBUTING.md) for dependency and CI updates
