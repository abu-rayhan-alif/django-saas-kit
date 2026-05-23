# Threat model

**Stories:** SAAS-701 (headers / CORS) | SAAS-702 (rate limiting) | **Layer:** L1–L2

High-level view of assets, threats, and mitigations for the Django SaaS Kit API. For vulnerability reporting, see [SECURITY.md](../../SECURITY.md).

---

## Assets and mitigations

| Asset | Threat | Mitigation |
|-------|--------|------------|
| **User credentials** | Brute force / credential stuffing | DRF throttling (`5/min` login, `100/min` authenticated API); Django password validators; Argon2 in production (see [SECURITY.md](../../SECURITY.md)) |
| **JWT access / refresh tokens** | Theft via XSS or network intercept | Short access lifetime; refresh rotation + blacklist; HTTPS in production; `HttpOnly` cookies if you move tokens to cookies in a fork |
| **API surface** | Host-header / open-proxy abuse | `ALLOWED_HOSTS` from environment; required in production |
| **Browser API clients** | Cross-origin abuse (CSRF-like data exfiltration) | `django-cors-headers` with explicit `CORS_ALLOWED_ORIGINS` (defaults from `FRONTEND_URL`) |
| **Transport** | Downgrade to HTTP, MITM | `SECURE_SSL_REDIRECT=True` in production; HSTS headers |
| **Clickjacking / XSS** | Framed admin/API, injected scripts | `X-Frame-Options: DENY`; Content-Security-Policy in production |
| **Multi-tenant data** | Cross-tenant privilege escalation | Tenant-scoped RBAC (`HasRolePermission`, `X-Tenant-ID` / URL tenant) |

---

## HTTP security headers (SAAS-701)

Production (`config.settings.prod`) enables browser and transport protections. Local development keeps most headers relaxed for ergonomics.

| Header / setting | Environment | Purpose |
|------------------|-------------|---------|
| **`ALLOWED_HOSTS`** | All (required in prod) | Rejects requests whose `Host` does not match configured domains — mitigates cache poisoning and password-reset hijacking |
| **`SECURE_SSL_REDIRECT`** | Prod: `True` | 301 redirect HTTP → HTTPS behind TLS-terminating proxy (`SECURE_PROXY_SSL_HEADER`) |
| **HSTS** (`Strict-Transport-Security`) | Prod | `SECURE_HSTS_SECONDS` (1 year), include subdomains, preload list eligible |
| **`X-Frame-Options: DENY`** | Prod | Prevents embedding the app in iframes (clickjacking) |
| **`X-Content-Type-Options: nosniff`** | Prod | Stops MIME-type sniffing |
| **`Content-Security-Policy`** | Prod | Restricts script/style/load sources; default policy in `config/settings/security.py` |
| **Secure cookies** | Prod | `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` |

### Content-Security-Policy (CSP)

Default policy (override with env `CONTENT_SECURITY_POLICY`):

```text
default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';
img-src 'self' data: https:; connect-src 'self'; frame-ancestors 'none';
base-uri 'self'; form-action 'self'
```

- **`frame-ancestors 'none'`** — aligns with `X-Frame-Options: DENY` for modern browsers.
- **`unsafe-inline`** — allows bundled **Swagger UI / ReDoc** on `/api/docs/` and `/api/redoc/`. Tighten in forks that disable interactive docs in production.

Implementation: `apps/common/middleware/content_security_policy.py` (no header when `CONTENT_SECURITY_POLICY` is empty).

### CORS

| Setting | Source | Notes |
|---------|--------|-------|
| `CORS_ALLOWED_ORIGINS` | Env CSV, else `FRONTEND_URL` | Explicit origins only — no `*` in production |
| `CORS_ALLOW_CREDENTIALS` | Default `True` | Required for cookie / credentialed SPA calls |
| `CORS_URLS_REGEX` | `^/api/.*$` | CORS preflight only on API routes |

```env
CORS_ALLOWED_ORIGINS=https://app.example.com,https://www.example.com
FRONTEND_URL=https://app.example.com
```

### Configuration map

| Concern | Location |
|---------|----------|
| CORS + `ALLOWED_HOSTS` base | `config/settings/base.py` |
| Prod TLS, HSTS, CSP | `config/settings/prod.py` |
| CSP default string | `config/settings/security.py` |
| CORS middleware | `corsheaders.middleware.CorsMiddleware` |

### Staging

`config.settings.staging` imports production security settings but sets `SECURE_SSL_REDIRECT=False` by default for HTTP-only staging URLs. HSTS and CSP still apply when served over HTTPS.

---

## Rate limiting (SAAS-702)

API rate limits use **Django REST framework throttling** backed by the default cache (Redis in production, locmem in tests). Exceeded limits return **`429 Too Many Requests`** in the unified error envelope:

```json
{
  "error": "throttled",
  "message": "Request was throttled. Expected available in 42 seconds.",
  "details": {}
}
```

### Default limits

| Scope | Rate | Applies to |
|-------|------|------------|
| **`login`** | **5 / minute** | `POST /api/v1/auth/token/` only (`LoginRateThrottle`) |
| **`user`** | **100 / minute** | Authenticated requests (all API views using default throttles) |
| **`anon`** | **20 / minute** | Unauthenticated requests (register, password reset, failed login, etc.) |

Override via environment:

```env
THROTTLE_LOGIN_RATE=5/minute
THROTTLE_USER_RATE=100/minute
THROTTLE_ANON_RATE=20/minute
```

### Exemptions

| Endpoint | Throttling |
|----------|------------|
| `GET /health/` | Disabled (liveness probes) |
| `GET /ready/` | Disabled (readiness probes) |

### Implementation map

| Component | Location |
|-----------|----------|
| Login throttle | `apps/common/throttling.py` → `LoginRateThrottle` |
| Login view | `apps/authentication/token_views.py` → `TokenObtainPairView` (`throttle_scope = "login"`) |
| Anon / user throttles | `apps/common/throttling.py` |
| Default classes + rates | `config/settings/base.py` → `REST_FRAMEWORK` |
| 429 error shape | `apps/common/exceptions.py` → `saas_exception_handler` |

### Operations notes

- Limits are **per cache key** (typically client IP for anonymous/login; user id when authenticated).
- For multi-instance deployments, use a **shared Redis cache** (already the default `CACHES` backend) so limits apply across all workers.
- Add edge rate limiting (CDN / API gateway) in production for DDoS protection — app-level throttling does not replace WAF.

---

## Out of scope (fork / production)

- WAF, bot management, geo blocking
- Global DDoS / per-IP limits at the CDN (complement app throttling)
- mTLS between services
- Field-level encryption at rest

---

## Related

- [SECURITY.md](../../SECURITY.md) — disclosure policy, Argon2, throttling examples
- [ADR 003 — Why JWT](../adr/003-why-jwt.md)
- [Observability](../observability.md)
