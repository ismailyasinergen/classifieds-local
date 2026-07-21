# v311 — Notification delivery migration rollout rehearsal

## Purpose

V311 packages the manually validated notification-delivery migration rehearsal
as a reusable, guarded operator script.

The rehearsal covers these exact migrations:

1. `accounts.0016_emailverificationstate_v306`
2. `listings.0024_notification_provider_outcomes_v307`
3. `listings.0025_notification_delivery_retention_v308`

It does not apply those migrations to the source development database.

## Command

Run from the repository root:

    bash scripts/rehearse_notification_delivery_migrations_v311.sh --confirm

Optional explicit database names:

    bash scripts/rehearse_notification_delivery_migrations_v311.sh \
      --confirm \
      --source-db classifieds_db \
      --clone-name test_classifieds_v311_rehearsal

The disposable database name must match `test_[a-z0-9_]+`.

## Safety contract

The rehearsal:

- requires explicit `--confirm` authorization;
- refuses unsafe PostgreSQL identifiers;
- refuses equal source and clone names;
- refuses to reuse an existing clone;
- records the source database OID;
- requires zero active source connections before template cloning;
- never calls `pg_terminate_backend`;
- never uses PostgreSQL `WITH (FORCE)` or `dropdb --force`;
- applies migrations only with `DB_NAME` pointing to the disposable clone;
- verifies that the source remains `ready_to_apply`;
- drops the clone only when the clone has zero active connections;
- leaves a connected clone in place rather than force-dropping it.

## Rehearsal sequence

1. Run the v310 read-only preflight against the source.
2. Require `status=ready_to_apply` and the exact three-migration plan.
3. Record the source database OID.
4. Require zero active source connections.
5. Create a distinct `test_`-prefixed PostgreSQL template clone.
6. Run the v310 preflight against the clone.
7. Review `python manage.py migrate --plan`.
8. Apply migrations to the disposable clone only.
9. Require clone status `already_applied`.
10. Run Django's general migration check against the clone.
11. Verify backfill and schema evidence.
12. Recheck the source preflight and OID.
13. Drop the disconnected disposable clone.

## Evidence contract

A successful clone must report:

- three applied target migration records;
- three target tables;
- eleven target columns on `NotificationDeliveryEvent`;
- four target indexes;
- three target constraints;
- one `EmailVerificationState` row for every cloned user;
- no unexpected provider receipt, retention evidence, or delivery-event rows.

## Manual validation evidence

The initial disposable rehearsal completed successfully against PostgreSQL 17.10:

- the source reported `ready_to_apply`;
- twelve cloned users produced twelve verification-state rows;
- all three target migrations applied successfully;
- the clone reported `already_applied`;
- all expected tables, columns, indexes, and constraints were present;
- the source database OID and migration state remained unchanged;
- the disposable clone was removed;
- the three development migrations remained unapplied.

## Failure handling

The script is fail-closed. A failure still triggers cleanup inspection.

When the disposable clone has active connections, the script does not terminate
those sessions and does not force-drop the database. The operator must inspect
the connection owner, close it safely, and remove the `test_` database manually
only after confirming that it is the intended disposable rehearsal clone.

## Scope

V311 adds no Django model, migration file, route, view, template, background
worker, production auto-migration behavior, or source application-data change.
