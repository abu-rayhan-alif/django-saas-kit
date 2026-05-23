# GitHub template repository setup (SAAS-B01)

Checklist for maintainers enabling **Use this template** on this repository.

## 1. Mark as template repository

1. Open the repo on GitHub → **Settings** → **General**.
2. Under **Repository name**, find **Template repository**.
3. Enable **Template repository** and save.

After this, the green **Use this template** button appears on the repo home page.

## 2. README screenshot

The README links to `docs/images/use-this-template.svg` (GitHub-style mockup).

Optional: replace it with a real screenshot after enabling the template:

1. Capture the repo header showing **Use this template**.
2. Save as `docs/images/use-this-template.png`.
3. Update the image path in [README.md](../../README.md) if you switch to PNG.

## 3. Verify CI on a template-generated repo

1. Click **Use this template** → **Create a new repository** (test org or personal account).
2. Clone the new repo and confirm `.github/workflows/ci.yml` is present.
3. Push a small commit to `main` (or open a PR to `main` / `develop`).
4. On GitHub → **Actions**, confirm workflows **Lint & Format**, **Tests**, and **Docker Build** complete.

CI does not require repository secrets: the workflow copies `.env.example` to `.env` and sets test `SECRET_KEY`, `DATABASE_URL`, and `REDIS_URL` inline.

If Actions are disabled on the new repo, enable them under **Settings** → **Actions** → **General**.

## 4. Acceptance criteria mapping

| Criterion | Where |
|-----------|--------|
| Template repository enabled | GitHub Settings (step 1 above) |
| README shows **Use this template** | [README.md](../../README.md) — *Start from this template* |
| CI runs on new repo from template | `.github/workflows/ci.yml` + verification (step 3) |
| `.env` from `.env.example` documented | README + `.env.example` header |
