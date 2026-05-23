# Architecture Decision Records (ADR)

An **ADR** captures a significant architectural choice: what we decided, why, and what we gave up.

## When to write an ADR

Write a new ADR when a change:

- Affects **multiple apps** or cross-cutting infrastructure (database, cache, auth, async)
- Is **hard to reverse** or expensive to change later
- Introduces a **new dependency** or replaces one
- Has **security, privacy, or compliance** impact (consider label `gdpr`)
- Needs team alignment before implementation

**Do not** write an ADR for routine bug fixes, small refactors, or single-endpoint tweaks — use the PR description and tests instead.

## Numbering rules

| Rule | Example |
|------|---------|
| Three-digit prefix, zero-padded | `001`, `002`, … `010` |
| Kebab-case slug after the number | `004-why-redis.md` |
| One decision per file | Split if two unrelated choices |
| Never reuse numbers | Deprecated ADRs stay in place; mark **Superseded by ADR-00N** |
| Sequential only | Next free number is `006` (after `005`) |

## Required format

Every ADR must include these sections **in order**:

1. **Context** — problem, requirements, constraints  
2. **Decision** — what we chose (be specific: libraries, config, boundaries)  
3. **Consequences** — positive, negative, and operational follow-ups  
4. **Alternatives** — options considered and why they were rejected or deferred  

Optional: **References**, **Status** (`Proposed` | `Accepted` | `Deprecated` | `Superseded`).

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [001](001-use-postgresql.md) | Use PostgreSQL | Accepted |
| [002](002-why-celery.md) | Why Celery | Accepted |
| [003](003-why-jwt.md) | Why JWT | Accepted |
| [004](004-why-redis.md) | Why Redis | Accepted |
| [005](005-django-environ-vs-python-decouple.md) | django-environ vs python-decouple | Accepted |

## How to add an ADR

1. Pick the next number (`006-...`).
2. Copy structure from [001-use-postgresql.md](001-use-postgresql.md).
3. Fill **Context → Decision → Consequences → Alternatives**.
4. Add a row to the index table above.
5. Open a PR with label `adr` and check **ADR updated** on the [PR template](../../.github/PULL_REQUEST_TEMPLATE.md).

## Related

- [Service layer architecture](../architecture/service-layer.md)
- [Contributing — ticket flow](../../CONTRIBUTING.md)
