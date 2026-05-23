# Observability — Sentry first, Prometheus later

**Story:** NEW-02 | **Layer:** L2

This guide explains **why** we prioritize Sentry before Prometheus, what is **`planned`** (not yet in the repo), and how to onboard when you deploy a fork.

> **No production code is required in the starter kit** for this story — integration is documentation-only until a follow-up implementation ticket.

---

## Roadmap

| Phase | Tool | Status | Purpose |
|-------|------|--------|---------|
| **1** | **Sentry** | **`planned`** | Exceptions, performance traces, release tracking |
| **2** | **Prometheus** (+ Grafana) | **`planned`** | Metrics, alerting, capacity planning |

**Why Sentry first?**

- Developers need **actionable stack traces** on the first production error — Sentry is optimized for this.
- Setup is one DSN and a few settings; no extra containers in `docker-compose.yml` for local dev.
- Prometheus shines after you know *what* breaks and need *how often* and *how hot* (RPS, latency percentiles, queue depth).

**Why Prometheus later?**

- Requires scrape targets, retention, alerting rules, and usually Grafana — more moving parts.
- Metrics complement errors; they rarely replace them for debugging a new 500 traceback.

See [ADR 006 — Sentry vs Prometheus](adr/006-sentry-vs-prometheus.md).

---

## Phase 1 — Sentry (`planned`)

### Environment variables

Add to `.env` (not required for local dev):

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `SENTRY_DSN` | Prod/staging | `https://xxx@o123.ingest.sentry.io/456` | Project DSN from Sentry |
| `SENTRY_ENVIRONMENT` | No | `staging` / `production` | Separates events per deploy |
| `SENTRY_RELEASE` | No | `django-saas-kit@0.1.0` | Git tag or CI build id |
| `SENTRY_TRACES_SAMPLE_RATE` | No | `0.1` | Performance trace sampling (0.0–1.0) |
| `SENTRY_ENABLED` | No | `True` | Gate SDK init (default `False` locally) |

Example `.env` block (copy when implementing):

```env
# --- Observability (planned — see docs/observability.md) ---
# SENTRY_ENABLED=False
# SENTRY_DSN=
# SENTRY_ENVIRONMENT=local
# SENTRY_RELEASE=0.1.0
# SENTRY_TRACES_SAMPLE_RATE=0.0
```

### Onboarding steps (`planned` implementation)

1. Create a project at [sentry.io](https://sentry.io/) → **Django** platform.
2. Copy the **DSN** into `SENTRY_DSN` for staging/production secrets (never commit real DSNs).
3. Install SDK (when you implement): `pip install sentry-sdk`
4. Initialize in `config/settings/prod.py` (example only — **not in repo yet**):

   ```python
   # planned — example for your fork
   if get_bool("SENTRY_ENABLED", default=False):
       import sentry_sdk
       from sentry_sdk.integrations.celery import CeleryIntegration
       from sentry_sdk.integrations.django import DjangoIntegration

       sentry_sdk.init(
           dsn=get_str("SENTRY_DSN"),
           environment=get_str("SENTRY_ENVIRONMENT", default="production"),
           release=get_str("SENTRY_RELEASE", default=""),
           traces_sample_rate=float(get_str("SENTRY_TRACES_SAMPLE_RATE", default="0.1")),
           integrations=[DjangoIntegration(), CeleryIntegration()],
           send_default_pii=False,
       )
   ```

5. Deploy → trigger a test error → confirm event in Sentry.
6. Configure alerts (email/Slack) for new issues and regression spikes.

### What Sentry covers vs gaps

| Covered (`planned`) | Not covered (use Phase 2) |
|---------------------|---------------------------|
| 500 tracebacks, Celery task failures | Request rate / error **rate** trends |
| Release regressions | Disk, CPU, Postgres connection pool |
| User context (if you opt in) | Custom business KPIs |

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
| Sentry | **Off** — leave `SENTRY_ENABLED=False` or unset |
| Prometheus | **Off** — avoids extra Compose services |

Use CI/staging for validating observability before production.

---

## Checklist before production

- [ ] Sentry DSN in secrets manager (`planned` wiring)
- [ ] `SENTRY_ENVIRONMENT` matches deploy name
- [ ] `send_default_pii=False` unless legal review approves PII (`gdpr` label)
- [ ] Prometheus scrape + dashboards (`planned`)
- [ ] Alerts routed to on-call channel

---

## Related

- [ADR 006 — Sentry vs Prometheus](adr/006-sentry-vs-prometheus.md)
- [Background jobs — failed task monitoring](background-jobs.md)
- [SECURITY.md](../SECURITY.md)
