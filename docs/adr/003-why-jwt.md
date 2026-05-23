# ADR 003 — Why JWT for API Authentication

**Status:** Accepted  
**Date:** 2026-05-23  
**Deciders:** Platform team  
**Story:** SAAS-201

---

## Context

The Django SaaS Kit exposes a REST API consumed by single-page applications, mobile clients, and third-party integrations. We need a stateless, scalable authentication mechanism that fits a multi-tenant architecture where requests are routed across multiple application servers.

### Requirements

- Stateless verification so any app-server replica can authenticate a request without a shared session store.
- Short-lived credentials to limit blast radius if a token is intercepted.
- A safe logout mechanism even for stateless tokens.
- Interoperability with standard HTTP `Authorization: Bearer` headers.

---

## Decision

Use **JSON Web Tokens (JWT)** via `djangorestframework-simplejwt` with the following configuration:

| Parameter | Value | Rationale |
|---|---|---|
| Access token lifetime | **15 minutes** | Short window limits exposure if stolen; clients must refresh proactively. |
| Refresh token lifetime | **7 days** | Balances session longevity with security; aligns with typical "remember me" UX expectations. |
| `ROTATE_REFRESH_TOKENS` | **True** | Each refresh call issues a new refresh token, invalidating the old one. Prevents replay of stolen refresh tokens. |
| `BLACKLIST_AFTER_ROTATION` | **True** | Used refresh tokens are stored in `rest_framework_simplejwt.token_blacklist`. Required for secure logout. |

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/auth/token/` | Login — exchange credentials for access + refresh tokens |
| `POST` | `/api/v1/auth/token/refresh/` | Rotate refresh token, get new access token |
| `POST` | `/api/v1/auth/token/blacklist/` | Logout — blacklist the current refresh token |

---

## Alternatives Considered

### Django Session Authentication

Django's built-in session auth stores session state server-side in a database or cache. This requires sticky sessions or a shared session backend for horizontal scaling. It is suitable for server-rendered apps but adds coupling for a pure REST API used by diverse clients.

**Rejected** because it requires shared state and is ill-suited for mobile/SPA/third-party consumers.

### django-oauth-toolkit (OAuth 2.0)

OAuth 2 is the industry standard for delegated authorization and supports scopes, client credentials, and third-party IdP flows. It is more complex to operate (client registry, token introspection endpoint, PKCE flow).

**Deferred** — OAuth 2 is the preferred long-term path if external integrations or social login are added. The JWT implementation uses the same `Authorization: Bearer` header convention, making a future migration non-breaking at the HTTP interface level.

### Opaque (random) tokens via `TokenAuthentication`

DRF's built-in `TokenAuthentication` issues random opaque tokens stored in the database. Every authenticated request hits the DB for token lookup. Offers simple revocation but does not scale gracefully under high read load.

**Rejected** because it reintroduces per-request database round-trips, undermining the stateless scaling goal.

---

## Consequences

**Positive**

- Access tokens are verified locally (HMAC signature check) — no DB round-trip per request.
- Horizontal scaling is trivial: any replica can verify any token.
- Refresh rotation + blacklisting gives us effective logout semantics without abandoning stateless verification for access tokens.
- `drf-spectacular` auto-generates correct `BearerAuth` security scheme in the OpenAPI schema.

**Negative / Trade-offs**

- The blacklist table grows over time and must be pruned. Run `python manage.py flushexpiredtokens` periodically (Celery beat task recommended).
- Access tokens cannot be individually revoked mid-lifetime (15 min max exposure window). For high-security operations (e.g., password change), callers should treat the access token as stale and re-authenticate.
- JWTs are larger than opaque tokens (~200–400 bytes vs ~40 bytes), slightly increasing request header size.

---

## References

- [djangorestframework-simplejwt docs](https://django-rest-framework-simplejwt.readthedocs.io/)
- [RFC 7519 — JSON Web Token](https://datatracker.ietf.org/doc/html/rfc7519)
- [OWASP JWT Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
