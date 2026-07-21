# v310 — Notification delivery migration rollout preflight

## Purpose

V310 adds a detailed, read-only operator preflight for the three notification
delivery migrations introduced in v306–v308:

- `accounts.0016_emailverificationstate_v306`;
- `listings.0024_notification_provider_outcomes_v307`;
- `listings.0025_notification_delivery_retention_v308`.

The preflight never applies or reverses a migration and never changes
application data.

## Command

Text output:

    python manage.py check_notification_delivery_migration_rollout

Structured output:

    python manage.py check_notification_delivery_migration_rollout --json

Fail-closed operator mode:

    python manage.py check_notification_delivery_migration_rollout --strict

Strict mode succeeds in two safe states:

- all three migrations are pending in the exact reviewed order and none of
  their future schema objects collide with the current database;
- all three migrations are applied and their required schema objects exist.

Strict mode fails for partial application, an unexpected migration plan,
schema-object collisions, missing post-application schema, an unsupported
database backend, or an inspection failure.

## Read-only evidence

The command reports only sanitized operational counts and identifiers:

- migration mode and target counts;
- exact pending or applied migration labels;
- schema collision and missing-object counts;
- the expected email-verification backfill row count;
- the notification delivery event row count;
- blocking check results and stable reason codes.

It does not print user email addresses, provider payloads, delivery recipients,
tokens, or database exception text.

## Production integration

`scripts/prod_preflight.sh` runs the v310 strict preflight before Django's
general read-only migration check:

    python manage.py migrate --check --noinput

The v310 command explains whether the reviewed notification migration set is
safe to apply. The existing v302 migration check continues to block application
startup while any committed migration remains unapplied.

## Operator rollout sequence

1. Take and verify a current PostgreSQL backup.
2. Run the v310 command with `--strict`.
3. Review `python manage.py migrate --plan`.
4. Apply migrations with the existing operator-controlled one-off deployment
   command.
5. Run the v310 strict command again and require `status=already_applied`.
6. Run the general v302 migration check and production preflight.
7. Start or restart application processes only after both checks pass.

Application rollback must not automatically reverse these migrations. Deploy
code compatible with the current additive schema or execute a separately
reviewed database rollback procedure.

## Scope

V310 adds no model, migration file, route, template, delivery attempt,
provider access, startup auto-migration, or application-data mutation.
