# Versioning (SAAS-B05)

This project uses **[Semantic Versioning 2.0.0](https://semver.org/)**:

```text
MAJOR.MINOR.PATCH
```

| Bump | When |
|------|------|
| **MAJOR** | Breaking API or incompatible configuration changes |
| **MINOR** | New features, backward-compatible |
| **PATCH** | Bug fixes, backward-compatible |

## Single source of truth

| Artifact | Location |
|----------|----------|
| Package / release version | `pyproject.toml` → `[project].version` |
| Changelog | [`CHANGELOG.md`](../CHANGELOG.md) |
| Git tag | `v0.1.0` (prefix `v` + semver) |
| README badge | [`CHANGELOG.md`](../CHANGELOG.md) (update shield when you bump version) |

The **OpenAPI** `info.version` in `SPECTACULAR_SETTINGS` describes the **HTTP API contract**
(e.g. `1.0.0`), not the repository release tag. Bump it when you ship breaking API changes
under `/api/v2/`, etc.

## Release checklist (maintainers)

1. Move changes from `[Unreleased]` to a new `## [x.y.z] - YYYY-MM-DD` section in `CHANGELOG.md`
2. Update `version` in `pyproject.toml`
3. Update the README version badge if not using the dynamic GitHub Release shield
4. Commit: `chore(release): vX.Y.Z`
5. Tag and push:

   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z
   ```

6. Create a **GitHub Release** from the tag (copy the version section from `CHANGELOG.md`):

   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z" --notes "$(sed -n '/^## \[X.Y.Z\]/,/^## \[/p' CHANGELOG.md | head -n -1)"
   ```

   Or use the GitHub UI: **Releases → Draft a new release → Choose tag `vX.Y.Z` → Paste changelog**.

7. (Optional) Switch the README badge to the dynamic release shield:

   ```markdown
   [![version](https://img.shields.io/github/v/release/abu-rayhan-alif/django-saas-kit?label=version&sort=semver)](https://github.com/abu-rayhan-alif/django-saas-kit/releases)
   ```

### Initial release (`v0.1.0`)

After merging changelog and versioning docs:

```bash
git add CHANGELOG.md docs/VERSIONING.md README.md CONTRIBUTING.md
git commit -m "chore(release): v0.1.0"
git tag -a v0.1.0 -m "v0.1.0 — initial release"
git push origin main
git push origin v0.1.0
```

Then publish **v0.1.0** on GitHub Releases with the `[0.1.0]` section from `CHANGELOG.md`.

[Keep a Changelog]: https://keepachangelog.com/
