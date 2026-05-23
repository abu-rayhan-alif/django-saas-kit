# ADR 006 — Sentry first, Prometheus later

**Status:** Accepted  
**Date:** 2026-05-23  
**Story:** NEW-02 | **Layer:** L2

---

## Context

Operators need visibility into the Django SaaS Kit in production: unhandled exceptions, slow requests, and eventually capacity metrics (CPU, queue depth, error rates).

Two common stacks:

| Tool | Primary strength |
|------|------------------|
| **Sentry** | Error tracking, stack traces, release health, breadcrumbs |
| **Prometheus** | Time-series metrics, alerting rules, Grafana dashboards |

Early-stage teams and L1/L2 boilerplate consumers benefit most from **fast feedback on failures** before investing in full metrics infrastructure.

---

## Decision

Adopt observability in **two phases**:

1. **Phase 1 (now — documented, `planned` in code):** [Sentry](https://sentry.io/) for exception and performance monitoring.
2. **Phase 2 (later — `planned`):** [Prometheus](https://prometheus.io/) + Grafana (or managed equivalent) for metrics, SLOs, and autoscaling signals.

Implementation guide: [docs/observability.md](../observability.md). **No SDK wiring ships in the starter repo** until a follow-up story; env vars and onboarding steps are documented for forks.

---

## Consequences

**Positive**

- Faster mean-time-to-detect for exceptions (Sentry) without running Prometheus in local Docker Compose
- Clear upgrade path to metrics without blocking initial SaaS delivery
- Lower local dev complexity (optional Sentry DSN only)

**Negative**

- No built-in request-rate / latency dashboards until Phase 2
- Two systems to operate in mature production (acceptable; different concerns)

**Operational**

- Tag Sentry events with `environment` and release version
- When Prometheus is added, scrape `/metrics` and Celery exporter — see observability doc

---

## Alternatives

### Prometheus only from day one

**Deferred** — excellent for SRE teams with existing Grafana; heavier onboarding for a starter kit and weak stack traces compared to Sentry for application errors.

### Datadog / New Relic all-in-one

**Deferred** — viable commercial option; higher cost and vendor lock-in. Documented as alternative in observability guide.

### OpenTelemetry single pipeline

**Deferred** — unified traces/metrics/logs is the long-term direction; Sentry + Prometheus remains a pragmatic stepping stone for Django teams.

---

## References

- [Observability guide](../observability.md)
- [Background jobs — monitoring](background-jobs.md)
