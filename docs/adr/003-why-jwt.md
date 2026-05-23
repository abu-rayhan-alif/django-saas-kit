# ADR 003 — Why JWT for API Authentication

**Status:** Accepted  
**Date:** 2026-05-23  
**Story:** SAAS-1003 / SAAS-201

---

## Context

The Django SaaS Kit exposes a REST API consumed by SPAs, mobile clients, and integrations. We need authentication that:

- Scales **horizontally** without sticky sessions
- Uses standard **`Authorization: Bearer`** headers
- Supports **logout** and refresh without storing session state on every access-token check
- Fits **multi-tenant RBAC** where the tenant is resolved per request (URL or header), not embedded only in the token

---

## Decision

Use **JSON Web Tokens (JWT)** via `djangorestframework-simplejwt`.

| Setting | Value | Notes |
|---------|-------|--------|
| Access token lifetime | **15 minutes** (env: `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`) | Short-lived access |
| Refresh token lifetime | **7 days** (env: `JWT_REFRESH_TOKEN_LIFETIME_DAYS`) | Session-like UX |
| `ROTATE_REFRESH_TOKENS` | `True` | New refresh on each refresh call |
| `BLACKLIST_AFTER_ROTATION` | `True` | Old refresh tokens invalidated |

**Endpoints** (under `/api/v1/auth/`):

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `token/` | Obtain access + refresh |
| `POST` | `token/refresh/` | Rotate refresh, new access |
| `POST` | `token/blacklist/` | Logout (blacklist refresh) |

OpenAPI documents `BearerAuth` via `drf-spectacular` in `SPECTACULAR_SETTINGS`.

---

## Consequences

**Positive**

- Access tokens verified locally (signature) — no DB lookup per request
- Any app replica can authenticate requests
- Refresh rotation + blacklist enables practical logout semantics
- Same header convention as future OAuth 2 migration

**Negative**

- Blacklist table grows — run `flushexpiredtokens` periodically (Celery beat recommended)
- Access tokens cannot be revoked mid-lifetime (max ~15 minutes exposure)
- Larger headers than opaque tokens (~200–400 bytes)

**Security**

- Never log tokens; use HTTPS in production (`SECURE_SSL_REDIRECT`)
- On password change, clients should discard tokens and re-login

---

## Alternatives

### Django session authentication

Server-side sessions require a shared session store or sticky load balancers.

**Rejected** for a stateless REST API consumed by diverse clients.

### django-oauth-toolkit (OAuth 2.0)

Industry standard for delegated auth, third-party clients, and scopes.

**Deferred** — preferred if social login or external integrations become first-class; HTTP `Bearer` interface stays compatible.

### DRF `TokenAuthentication` (opaque DB tokens)

Random tokens stored in PostgreSQL; validated on every request.

**Rejected** — per-request DB round-trip conflicts with horizontal scaling goals.

### API keys only

Simple for machine-to-machine; weak for interactive user sessions and refresh flows.

**Rejected** as the primary user auth mechanism; may complement JWT for webhooks in a future ADR.

---

## References

- [djangorestframework-simplejwt](https://django-rest-framework-simplejwt.readthedocs.io/)
- [RFC 7519 — JWT](https://datatracker.ietf.org/doc/html/rfc7519)
- [OWASP JWT Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
