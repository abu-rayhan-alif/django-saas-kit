# GitHub Project board setup (SAAS-1002)

Use a **GitHub Project** (v2) to track work from backlog to done.

## Create the board

1. Open the repository on GitHub → **Projects** → **New project**
2. Choose **Board** layout
3. Name it **Django SaaS Kit** (or your fork name)

## Columns

Create exactly these status columns:

| Column | Purpose |
|--------|---------|
| **Backlog** | Triaged issues and ideas not started |
| **In Progress** | Active development |
| **In Review** | Open PRs awaiting review |
| **Done** | Merged or closed |

In Project settings, map workflow statuses to these names (GitHub may default to
*Todo / In progress / Done* — rename to match the table above).

## Link issues and PRs

- Add issues from **Backlog** when accepted from GitHub Issues (public)
- Move to **In Progress** when a branch is opened
- Move linked PRs to **In Review** on open
- Move to **Done** when the PR merges or the issue closes

## Automation (optional)

Under **Workflows** in the project:

- When a PR is opened → set status **In Review**
- When a PR is merged → set status **Done**
- When an issue is closed → set status **Done**

## Ticket sources

| Stage | Tool |
|-------|------|
| Private planning | Personal Jira (or equivalent) |
| Public tracking | GitHub Issues + this Project board |

See [CONTRIBUTING.md](../../CONTRIBUTING.md#ticket-flow).
