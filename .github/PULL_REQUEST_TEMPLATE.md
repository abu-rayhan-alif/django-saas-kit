## Summary

<!-- What does this PR do? Link issues: Fixes #123, Relates to SAAS-XXXX -->

## Type of change

- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change (fix or feature with migration/API impact)
- [ ] Documentation only
- [ ] CI / tooling / governance

## How to test

<!-- Commands you ran, or steps for reviewers -->

```bash
make lint
make test
# optional: make dev
```

## PR checklist

- [ ] **Tests passed** — `make test` (or `pytest`) green locally / CI
- [ ] **Linted** — `make lint` (ruff + mypy) passes
- [ ] **ADR updated** (if arch change) — new or updated file under `docs/adr/`
- [ ] **Docs updated** — README, how-to, or `CUSTOMIZATION.md` as needed
- [ ] **Breaking change noted** — `CHANGELOG.md` + migration/API notes (or N/A)
- [ ] No secrets committed (`.env` stays gitignored)
- [ ] Appropriate labels applied (`adr`, `security`, `testing`, `gdpr`, `docs`, etc.)

## Screenshots / API notes

<!-- Optional: Swagger changes, OpenAPI diff, migration commands -->
