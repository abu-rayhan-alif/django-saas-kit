# Observability

**Stories:** SAAS-601 (structured logging) | SAAS-602 (health / readiness) | SAAS-603 (Sentry) | NEW-02 (Prometheus roadmap)

---

## Health and readiness (SAAS-602)

Orchestrators (Kubernetes, Docker Compose, load balancers) need two different probes:

| Endpoint | Purpose | Checks | Success | Failure |
|----------|---------|--------|---------|---------|
| `GET /health/` | **Liveness** — is the process alive? | None (in-process only) | `200` + `{"status":"ok"}` | *(n/a — restart if TCP/HTTP fails)* |
| `GET /ready/` | **Readiness** — can this instance take traffic? | PostgreSQL + Redis | `200` + checks all `ok` | `503` + `{"status":"not_ready",...}` |

Both endpoints are **unauthenticated** (`AllowAny`, no JWT).

### Response examples

**Liveness** (`/health/`):

```json
{"status": "ok"}
```

**Readiness** (`/ready/`) — success:

```json
{
  "status": "ok",
  "checks": {"database": "ok", "redis": "ok"}
}
```

**Readiness** — dependency down (`503`):

```json
{
  "status": "not_ready",
  "checks": {"database": "ok", "redis": "error"}
}
```

### Kubernetes probes

Use **liveness** on `/health/` so a wedged worker can restart without depending on Postgres/Redis (avoids restart loops when only the DB is down). Use **readiness** on `/ready/` so the Service stops routing traffic until dependencies recover.

```yaml
# deployment.yaml (web container) — example
spec:
  containers:
    - name: web
      ports:
        - containerPort: 8000
      livenessProbe:
        httpGet:
          path: /health/
          port: 8000
        initialDelaySeconds: 10
        periodSeconds: 10
        timeoutSeconds: 3
        failureThreshold: 3
      readinessProbe:
        httpGet:
          path: /ready/
          port: 8000
        initialDelaySeconds: 5
        periodSeconds: 5
        timeoutSeconds: 3
        failureThreshold: 3
```

| Probe | Path | When it fails | Typical action |
|-------|------|---------------|----------------|
| Liveness | `/health/` | Process not responding | kubelet **restarts** the pod |
| Readiness | `/ready/` | DB or Redis unreachable | Pod removed from **Service endpoints** (no restart) |

**Ingress / ALB:** point health checks at `/ready/` if you only want healthy instances behind the load balancer; keep liveness on `/health/` for the pod spec.

### Implementation map

| Component | Location |
|-----------|----------|
| Liveness view | `apps/common/views.py` → `HealthCheckView` |
| Readiness view | `apps/common/views.py` → `ReadinessCheckView` |
| DB + Redis probes | `apps/common/health_checks.py` |
| URL routes | `config/urls.py` |

---

## Structured logging (SAAS-601)

Every HTTP request and Celery task emits **structured logs** via [structlog](https://www.structlog.org/). Logs include correlation IDs so you can trace a single user action across the API and background workers.

### Correlation IDs

| Context | Field | Source |
|---------|--------|--------|
| HTTP request | `request_id` | Generated per request (UUID v4), or taken from `X-Request-ID` |
| Celery worker | `trace_id` | Copied from the publishing request’s `request_id`, or a new UUID for beat/CLI tasks |

**Response header:** `X-Request-ID` is set on every HTTP response (echoes the client value when provided).

### Output format by environment

| Environment | `STRUCTLOG_JSON` | Output |
|-------------|------------------|--------|
| **Local / dev** (`config.settings.local`) | `False` | Human-readable colored console |
| **Production / staging** (`config.settings.prod`) | `True` | One JSON object per line (for Loki, CloudWatch, Datadog, etc.) |

Override with env var `STRUCTLOG_JSON=True|False` if needed (e.g. JSON locally to test parsers).

### Logging policy

1. **Use structlog** — `logger = structlog.get_logger(__name__)` in application code (not bare `print` or unstructured strings).
2. **Structured keys** — pass fields as keyword arguments: `logger.info("user_created", user_id=user.pk)` so they appear in JSON output.
3. **Do not log secrets** — never log passwords, tokens, API keys, or full `Authorization` headers.
4. **PII** — avoid logging email, phone, or national IDs unless required and approved; prefer opaque IDs (`user_id`, `tenant_id`).
5. **Levels**
   - `DEBUG` — verbose diagnostics (off in production root logger).
   - `INFO` — normal lifecycle (request handled, task completed).
   - `WARNING` — recoverable issues (retries, deprecations).
   - `ERROR` / `exception` — failures needing attention.
6. **Correlation** — rely on bound `request_id` / `trace_id`; do not invent parallel ID fields unless integrating an external trace system (OpenTelemetry follow-up).
7. **Celery** — tasks enqueued during a request automatically propagate `trace_id`; idempotent tasks should still log `user_id` / business keys for support.

### Example log lines

**Local (console):**

```text
2026-05-23T12:00:00.123456Z [info     ] user_created          request_id=3f2504e0-4f89-11d3-9a0c-0305e82c3301 user_id=42
```

**Production (JSON):**

```json
{"event": "user_created", "request_id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301", "user_id": 42, "level": "info", "timestamp": "2026-05-23T12:00:00.123456Z", "logger": "services.users.user_service"}
```

### Implementation map

| Component | Location |
|-----------|----------|
| structlog + Django `LOGGING` | `apps/common/logging_config.py` |
| Request middleware | `apps/common/middleware/request_context.py` |
| Celery `trace_id` signals | `apps/common/celery_logging.py` |
| Startup wiring | `apps/common/apps.py` → `CommonConfig.ready()` |

### Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `STRUCTLOG_JSON` | No | `False` in base; overridden per settings module | Force JSON (`True`) or console (`False`) |

---

## Why Sentry before Prometheus?

We ship observability in phases so teams get value quickly without running a full metrics stack on day one.

| Order | Tool | Status | Rationale |
|-------|------|--------|-----------|
| 1 | **structlog** (SAAS-601) | Implemented | Correlation IDs (`request_id`, `trace_id`) in every log line |
| 2 | **Sentry** (SAAS-603) | Implemented | Actionable stack traces on the first production 500 — one DSN, no extra containers |
| 3 | **Prometheus** (NEW-02) | Planned | Request rates, latency percentiles, queue depth — after you know *what* breaks |

**Why Sentry before Prometheus?**

- **Faster MTTR on exceptions** — Sentry groups errors, shows breadcrumbs, and links releases; you do not need scrape targets, retention, or Grafana to debug a new traceback.
- **Lower local cost** — omit `SENTRY_DSN` and the SDK never initializes (silent skip); Prometheus usually adds services or agents to Compose/K8s.
- **Complements logs** — structlog `request_id` / `trace_id` are copied to Sentry tags so log lines and issues match.
- **Different question** — Sentry answers *“what failed and where?”*; Prometheus answers *“how often and how hot?”* Metrics rarely replace stack traces for a brand-new 500.

See [ADR 006 — Sentry vs Prometheus](adr/006-sentry-vs-prometheus.md).

---

## Sentry (SAAS-603)

Error monitoring via [sentry-sdk](https://docs.sentry.io/platforms/python/integrations/django/). **No DSN → no initialization** (startup continues normally).

### What is captured automatically

| Source | Mechanism |
|--------|-----------|
| Uncaught Django / middleware errors | `DjangoIntegration` |
| DRF unhandled 500s | `saas_exception_handler` → `capture_exception` |
| Celery task failures | `CeleryIntegration` |
| Correlation | `before_send` adds `request_id` / `trace_id` tags from structlog |

Handled API errors (validation 400, auth 401, etc.) are **not** sent to Sentry.

### Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SENTRY_DSN` | No | *(unset)* | Project DSN — **only gate**; empty/missing = Sentry off |
| `SENTRY_ENVIRONMENT` | No | `production` | `staging`, `production`, etc. |
| `SENTRY_RELEASE` | No | *(none)* | Git tag or CI build id |
| `SENTRY_TRACES_SAMPLE_RATE` | No | `0.0` | Performance traces (0.0–1.0); raise in staging if needed |

```env
# Staging/production secrets (never commit a real DSN)
SENTRY_DSN=https://key@o123.ingest.sentry.io/456
SENTRY_ENVIRONMENT=staging
SENTRY_RELEASE=django-saas-kit@0.1.0
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### Onboarding

1. Create a project at [sentry.io](https://sentry.io/) → **Django**.
2. Set `SENTRY_DSN` in your secrets manager for staging/production.
3. Deploy → trigger a test 500 → confirm the issue in Sentry (tags should include `request_id` when the error occurred during an HTTP request).
4. Configure alerts (email/Slack) for new issues and regressions.

### Implementation map

| Component | Location |
|-----------|----------|
| `init_sentry()` | `apps/common/sentry.py` |
| Startup | `apps/common/apps.py` → `CommonConfig.ready()` |
| DRF 500 capture | `apps/common/exceptions.py` |

### What Sentry covers vs gaps

| Covered | Not covered (Prometheus phase) |
|---------|-------------------------------|
| 500 tracebacks, Celery task failures | Request rate / error **rate** trends |
| Release regressions | Disk, CPU, Postgres pool saturation |
| `request_id` / `trace_id` tags | Custom business KPI dashboards |

---

## Phase 2 — Prometheus (`planned`)

### Environment variables

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `PROMETHEUS_ENABLED` | No | `True` | Expose `/metrics` endpoint |
| `PROMETHEUS_METRICS_PATH` | No | `/metrics` | Scrape path (protect in prod) |
| `PROMETHEUS_MULTIPROC_DIR` | No | `/tmp/prometheus` | Gunicorn multi-worker mode only |

Example `.env` block:

```env
# --- Metrics (planned — see docs/observability.md) ---
# PROMETHEUS_ENABLED=False
# PROMETHEUS_METRICS_PATH=/metrics
```

### Onboarding steps (`planned` implementation)

1. Add **django-prometheus** or **prometheus_client** + middleware in your fork.
2. Run **Prometheus** server (or use managed Grafana Cloud/Mimir).
3. Scrape targets:
   - Django app (`/metrics`)
   - **Redis** exporter (optional)
   - **Postgres** exporter (optional)
   - **Celery** exporter or flower metrics (optional)
4. Create Grafana dashboards: HTTP latency, 5xx rate, Celery queue length.
5. Alertmanager rules: error rate > threshold, worker down, Redis memory high.

### Suggested metrics (when implemented)

| Metric | Type | Use |
|--------|------|-----|
| `http_requests_total` | Counter | Traffic by status |
| `http_request_duration_seconds` | Histogram | Latency SLO |
| `celery_task_failures_total` | Counter | Background job health |

---

## Local development

| Tool | Local default |
|------|----------------|
| structlog | **On** — console format, `request_id` on API responses |
| Sentry | **Off** — omit `SENTRY_DSN` |
| Prometheus | **Off** — avoids extra Compose services |

Use CI/staging for validating JSON log shipping and observability before production.

---

## Checklist before production

- [x] Liveness `/health/` and readiness `/ready/` wired for probes (SAAS-602)
- [x] structlog JSON logs + `request_id` / `trace_id` (SAAS-601)
- [x] Sentry SDK wired; optional via `SENTRY_DSN` (SAAS-603)
- [ ] Log aggregation sink configured (Loki, CloudWatch, etc.)
- [ ] `SENTRY_DSN` in secrets manager (staging/production)
- [ ] `SENTRY_ENVIRONMENT` matches deploy name
- [ ] `send_default_pii=False` unless legal review approves PII (`gdpr` label)
- [ ] Prometheus scrape + dashboards (`planned`)
- [ ] Alerts routed to on-call channel

---

## Related

- [ADR 006 — Sentry vs Prometheus](adr/006-sentry-vs-prometheus.md)
- [Background jobs — failed task monitoring](background-jobs.md)
- [SECURITY.md](../SECURITY.md)
