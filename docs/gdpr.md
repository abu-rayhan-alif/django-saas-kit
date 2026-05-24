# GDPR & Data Privacy

This document describes how Django SaaS Kit handles personal data in compliance with GDPR and general data-minimisation principles.

---

## Log Redaction Policy

### Rule

**Never log passwords, raw tokens, or full email addresses.**

Structured logs are shipped to external aggregators (e.g. CloudWatch, Datadog, Loki). Any sensitive value that appears in a log line is effectively persisted in an external system outside Django's access controls, which violates GDPR's data-minimisation requirement (Article 5(1)(c)) and creates a credential-exposure risk.

### Enforcement

A structlog processor — `redact_sensitive_fields` in `apps/common/logging_config.py` — runs on every log event (both structlog and stdlib records forwarded through `ProcessorFormatter`). It replaces the value of any blocked field with the literal string `[REDACTED]` before the event reaches any renderer or transport.

The processor is inserted at the end of `shared_processors()` so it runs after context variables are merged but before JSON/console rendering.

### Field Blocklist

The following keyword arguments must **never** carry real values in logs:

| Field name | Reason |
|---|---|
| `password` | Direct credential |
| `new_password` | Direct credential |
| `old_password` | Direct credential |
| `confirm_password` | Direct credential |
| `token` | Raw session/reset token |
| `access_token` | JWT bearer token |
| `refresh_token` | JWT refresh token |
| `reset_token` | Password-reset token |
| `id_token` | OIDC identity token |
| `authorization` | HTTP Authorization header value |
| `email` | PII — full email address |
| `secret` | Generic secret |
| `api_key` | API credential |
| `secret_key` | Signing secret |
| `credit_card` | Financial PII |
| `ssn` | National identifier |

To add a new sensitive field, extend `SENSITIVE_FIELDS` in [`apps/common/logging_config.py`](../apps/common/logging_config.py) and add a row to this table.

### What you CAN log

- Opaque identifiers (`user_id`, `tenant_id`, `request_id`, `trace_id`)
- Usernames (not email addresses)
- Timestamps, HTTP methods, status codes, durations
- Partial/masked representations produced by your own code (e.g. `alice@***.com`)

### Code example

```python
# BAD — email and token end up in the log aggregator
log.info("password_reset_requested", email=user.email, token=token)

# GOOD — use opaque IDs only
log.info("password_reset_requested", user_id=user.pk)
```

---

## Right to be Forgotten (Article 17)

### Policy

Django SaaS Kit implements a two-mode erasure strategy.

| Mode | User row | Child records | When to use |
|------|----------|---------------|-------------|
| **Anonymize** (default) | Kept — PII fields overwritten with random placeholders | Hard-deleted | Preferred: preserves audit-trail integrity while removing all identifiable data |
| **Hard delete** (`--hard-delete`) | Permanently removed | Cascaded / SET_NULL | Use when the user row itself must not exist (e.g. legal hold lifted, test data) |

### What counts as personal data

The following fields on `AUTH_USER_MODEL` are considered PII and are wiped in anonymize mode:

- `username` → `deleted_<random12hex>`
- `email` → `deleted_<random12hex>@deleted.invalid`
- `first_name` → `""`
- `last_name` → `""`
- `password` → set unusable (hashed sentinel, no plaintext)
- `is_active` → `False`

### FK model handling

| Model | FK field | `on_delete` | Action taken |
|-------|----------|-------------|--------------|
| `Notification` | `user` | CASCADE | **Hard-deleted** in both modes (notification bodies are personal content) |
| `UserTenantRole` | `user` | CASCADE | **Hard-deleted** in both modes (membership is personal data) |
| `UserTenantRole` | `assigned_by` | SET_NULL | Left to Django — no PII leak (assignment record survives, auditor identity nulled) |
| `BaseModel` | `created_by`, `updated_by`, `deleted_by` | SET_NULL | Left to Django — audit rows survive with a null reference |
| `OutstandingToken` (simplejwt) | `user` | SET_NULL | **Explicitly deleted** — simplejwt uses SET_NULL so tokens must be revoked manually |

### Usage

```bash
# Anonymize — wipes PII, keeps user row (recommended default)
python manage.py delete_user_data <user_id>

# Hard-delete — removes user row entirely
python manage.py delete_user_data <user_id> --hard-delete

# Skip confirmation prompt (CI / scripted erasure workflows)
python manage.py delete_user_data <user_id> --no-input
```

The command prints a summary of what was deleted before prompting for confirmation, and emits a structured log event (`gdpr.anonymize` or `gdpr.hard_delete`) that log aggregators can alert on.

### Extending for new models

When you add a new model that holds user PII:

1. Decide which `on_delete` behaviour is appropriate (`CASCADE` for personal content, `SET_NULL` for audit references).
2. If the FK uses `SET_NULL` and the data is personal, add an explicit deletion step in `GDPRService._delete_<model>` and call it from both `anonymize()` and `hard_delete()`.
3. Add a row to the FK table above.

---

## Data Retention

*(Placeholder — fill in your retention schedule, e.g. logs purged after 30 days, DB records after N years.)*

---

## Data Subject Rights

*(Placeholder — describe how users can request export or deletion of their data.)*

---

## Sub-processors

*(Placeholder — list any third-party services that process personal data: email provider, log aggregator, error tracker, etc.)*
