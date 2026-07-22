# v316 — Notification-delivery migration rollout completion

V316_NOTIFICATION_DELIVERY_MIGRATION_ROLLOUT_COMPLETION=1

## Purpose

V316 records the completed and verified development-database rollout of the
three notification-delivery migrations prepared in v306 through v315.

The rollout state is now `post_apply`. This checkpoint documents verification
of the resulting database state; it does not introduce another migration
application command.

## Completed migration set

The exact applied migrations are:

    accounts.0016_emailverificationstate_v306
    listings.0024_notification_provider_outcomes_v307
    listings.0025_notification_delivery_retention_v308

No target migration remains pending.

## Post-apply database contract

The read-only v310 rollout preflight reports:

    status=already_applied
    migration_mode=post_apply
    applied_target_count=3
    pending_target_count=0
    pending_plan=[]
    blocking_not_ready_count=0
    read_only=true
    mutation_allowed=false

All required target tables, columns, indexes, and constraints are present.

## Data verification

The verified development-database state includes:

- 12 authentication users;
- 12 email-verification-state rows;
- 12 distinct users represented by those verification-state rows;
- 24 listings;
- zero notification-delivery-event rows;
- zero provider-outcome-receipt rows;
- zero retention-evidence rows;
- 64 recorded Django migrations;
- 34 public application tables.

The email-verification backfill therefore produced one verification-state row
for every existing user.

## Validation evidence

Post-apply validation completed successfully:

- 71 focused v306-v310 tests passed;
- the complete Django suite passed with 2,806 tests;
- Django system check passed;
- `python manage.py migrate --check --noinput` passed;
- the v310 post-apply rollout contract passed;
- `/healthz/` returned application and database status `ok`;
- the verified pre-application PostgreSQL backup and checksum remained valid.

## Backup evidence

The retained pre-application backup pair is:

    backups/postgres_20260722_041333.sql.gz
    backups/postgres_20260722_041333.sql.gz.sha256

The compressed backup remained gzip-valid and its SHA-256 sidecar verification
passed after rollout validation.

The backup payload remains ignored and is not included in the tracked
checkpoint.

## Failure and recovery boundary

No automatic rollback, reverse migration, or database restore was performed.

The verified post-apply state is healthy, so restoring the pre-application
backup would discard the successfully migrated state and is not part of this
checkpoint.

Any future recovery decision must remain a separate, explicitly reviewed
operator procedure.

## Repository scope

V316 adds only:

- `backend/listings/test_notification_delivery_migration_rollout_completion_v316.py`;
- `docs/notification_delivery_migration_rollout_completion_v316.md`.

V316 adds no model, migration file, route, view, template, management command,
database application script, startup behavior, service lifecycle operation,
backup artifact, restore operation, reverse migration, or automatic rollback.

## Incident record

During an attempted candidate-generation command, a malformed nested heredoc
caused shell parsing to continue outside the intended generator. The existing
three reviewed migrations were consequently applied to the development
database.

The repository remained unchanged and no partial V316 candidate file was
created. Immediate read-only inspection confirmed that all three migrations
completed successfully, their schema objects were present, the 12-user
verification-state backfill was complete, and the retained backup remained
valid.

Focused and full regression verification then confirmed the healthy post-apply
state recorded by this checkpoint.
