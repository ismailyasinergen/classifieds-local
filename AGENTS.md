# Repository Guidelines

## Repository Baseline

- Project: local Django classifieds marketplace
- Windows root: `C:\Users\ismai\Desktop\classifieds_local`
- Git Bash root: `/c/Users/ismai/Desktop/classifieds_local`
- Primary branch: `main`
- Completed checkpoint: commit `f4a64e7`, tag `project-checkpoint-v279-recent-price-drop-sort`
- Next version: `v280`
- Docker Compose Django service: `web`

Begin new feature work only from the clean completed checkpoint. Work on one numbered version at a time; never reuse a version number or modify an existing checkpoint.

## Project Structure & Architecture

The stack is Django, PostgreSQL, Docker Compose, and Nginx. Django code lives in `backend/`, with configuration and root URLs in `backend/config/`. Primary apps are `backend/listings/`, `backend/categories/`, and `backend/accounts/`; other domain apps include `conversations`, `pages`, and `promotions`.

Keep models, views, forms, commands, migrations, templates, and tests in their owning app. Shared templates are in `backend/templates/`; app templates are namespaced, for example `backend/listings/templates/listings/`. Nginx configuration is under `nginx/`, scripts under `scripts/`, and version documentation under `docs/`. Do not commit runtime data from `backend/media/` or `backend/staticfiles/`.

## Build, Test, and Development Commands

Run all Django commands inside the `web` container:

```bash
docker compose exec -T web python manage.py check
docker compose exec -T web python manage.py makemigrations --check --dry-run
docker compose exec -T web python manage.py test --verbosity 1
```

Use `docker compose up --build -d` to build and start PostgreSQL, Django/Gunicorn, and Nginx. Use `docker compose logs -f web` for application logs and `docker compose exec -T web python manage.py migrate` to apply migrations. During iteration, target the affected module, for example:

```bash
docker compose exec -T web python manage.py test listings.test_recent_price_drop_sort_v279 --verbosity 1
```

## Mandatory Version Workflow

For every numbered version:

1. Inspect the relevant implementation and tests before editing.
2. State the implementation plan.
3. Make the smallest coherent change.
4. Add focused regression tests and concise technical documentation under `docs/`.
5. Run `git diff --check`.
6. Run Django system checks.
7. Run the migration dry-run check.
8. Run targeted tests.
9. Run the complete Django regression suite.
10. Inspect the final diff and changed-file scope.
11. Commit only when every validation passes and the task explicitly authorizes checkpoint completion.
12. Create the checkpoint tag only after the commit succeeds.
13. Confirm that the working tree is clean.

Never claim completion before the full suite passes and the authorized checkpoint is confirmed.

## Testing Guidelines

Tests use Django's test runner and live in `tests.py`, `test_*.py`, or app `tests/` packages. Each feature should cover applicable cases from this matrix:

- expected behavior plus invalid or missing input;
- backward compatibility and public/category browse behavior;
- pagination and query-string preservation;
- saved-search compatibility;
- deterministic ordering with stable tie-breakers;
- permissions and access control;
- stale or mismatched data;
- migration status.

There is no configured coverage threshold, but the full regression suite is mandatory before a commit. Warnings intentionally produced by permission, not-found, method-not-allowed, or bad-request tests are acceptable when tests pass. Never weaken or remove a test merely to obtain a passing suite. Update an older contract test only for an intentional architecture change with backward compatibility still covered.

## Coding Style & Design Requirements

Use four-space indentation and Django/Python conventions: `snake_case` for functions, variables, and modules; `PascalCase` for classes; and descriptive `test_...` names. No repository-wide formatter or linter is configured, so match adjacent code and existing version-marker conventions.

Preserve existing behavior unless the specification changes it. Prefer shared helpers over duplicated query logic, avoid N+1 queries, use deterministic ordering, and keep modules focused. Maintain saved-search and URL-query compatibility and preserve accessibility behavior. Do not add dependencies without explicit justification, introduce migrations unless required, or alter unrelated files.

## Git & Checkpoint Safety

Never use destructive or history-rewriting operations, including `git reset --hard`, `git clean`, `git checkout -- .`, `git restore .`, force pushes, commit amendment, branch/tag deletion, or rebasing published checkpoints. Do not stash unless explicitly instructed.

Do not create a commit or tag unless the task explicitly authorizes completing the checkpoint. Before committing, verify that only expected files changed:

```bash
git status --short
git diff --check
git diff --stat
git diff
git diff --cached --check
```

Keep Git output noninteractive by setting `GIT_PAGER=cat` and `PAGER=cat` (or using the shell-equivalent environment syntax).

Commits use short, imperative, sentence-case subjects, such as `Add recent price drop browse sort`. Tags follow `project-checkpoint-v<VERSION>-<feature-slug>`, for example `project-checkpoint-v280-price-drop-period-filter`.

## Pull Requests, Security & Configuration

Pull requests should explain the problem and solution, list validation commands and test counts, note migration or configuration effects, link relevant issues, and include screenshots for UI changes. Copy local settings from `.env.example`; never commit `.env`, credentials, database dumps, uploaded media, or generated test artifacts. Review production-sensitive changes against `.env.production.example` and `README_PRODUCTION.md`.

## Communication & Completion Report

Give brief progress updates and report regressions and failed tests immediately. Explain actual root causes; do not conceal failures. At completion, report the commit hash, tag, changed files, targeted test count, full regression test count, migration result, and final Git status.

## Current Feature State

The project is complete through `v279`. That version introduced `sort=recent_price_drop`, valid current-reduction filtering, newest-reduction-first ordering, main and category browse integration, active-filter labels, pagination and saved-search preservation, public sort-menu support, and compatibility with the `v278` `price_drops=1` filter. Preserve these behaviors unless a later specification explicitly changes them.
