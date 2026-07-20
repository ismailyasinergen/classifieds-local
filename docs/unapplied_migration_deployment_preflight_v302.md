# v302 — Unapplied migration deployment preflight

## Purpose

v302 prevents application processes and schema-dependent maintenance commands
from starting against an older database schema.

The preflight uses Django's built-in read-only command:

    python manage.py migrate --check --noinput

This command exits non-zero when unapplied migrations exist and never applies
a migration.

## Environment contract

`DJANGO_AUTO_MIGRATE` controls entrypoint behavior.

- The entrypoint itself defaults to `0`, which is fail-closed and read-only.
- Local Docker Compose explicitly supplies `1` and preserves automatic
  migration application for development.
- Production Docker Compose explicitly supplies `0`.
- Invalid values stop startup before any schema-dependent command runs.

## Operator-controlled production deployment

Validate the deployment first:

    bash scripts/prod_preflight.sh

When pending migrations are reported, review the plan:

    docker compose \
      -f docker-compose.yml \
      -f docker-compose.prod.yml \
      --env-file .env.production \
      run --rm --entrypoint "" \
      web python manage.py migrate --plan

Apply the reviewed migrations as a separate operator action:

    docker compose \
      -f docker-compose.yml \
      -f docker-compose.prod.yml \
      --env-file .env.production \
      run --rm --entrypoint "" \
      web python manage.py migrate --noinput

Rerun the production preflight before starting or restarting the application.

## Startup safety order

In fail-closed mode, migration verification completes before:

- expired-listing archival;
- featured-placement expiry;
- promotion expiry;
- static-file collection;
- Gunicorn or another application command.

A pending migration blocks every schema-dependent startup action.

## Rollback-safe operating guidance

Before applying production migrations:

1. take and verify a current database backup;
2. review the migration plan;
3. confirm the code and migration set belong to the same checkpoint;
4. apply migrations as a separate operator action;
5. rerun the read-only preflight before serving traffic.

Do not automatically reverse migrations during an application rollback.
Deploy code compatible with the current schema or execute an explicitly
reviewed migration rollback procedure.

## Repository portability

The root `.gitattributes` file enforces `LF` line endings for every shell
script with this exact rule:

    *.sh text eol=lf

This prevents Windows Git configurations such as `core.autocrlf=true` from
converting container entrypoints into invalid `CRLF` shell scripts.

## Validation evidence

The completed v302 candidate recorded:

- 6 focused deployment-preflight tests passing;
- 66 related release and deployment tests passing;
- the complete serial regression suite passing all 2,663 tests in
  1408.896 seconds;
- Django system checks with zero issues;
- `makemigrations --check --dry-run` reporting no changes;
- `migrate --check --noinput` passing against the development database;
- successful development and production-example Compose rendering;
- the exact nine-file implementation scope remaining intact.

The development database was observed fully migrated through listings migration
`0023_listingpricehistory_discount_guardrail_v293`. v302 validation did not run
`migrate` against that database.

## Scope

v302 adds no model, schema migration, route, background worker, or automatic
production data mutation.
