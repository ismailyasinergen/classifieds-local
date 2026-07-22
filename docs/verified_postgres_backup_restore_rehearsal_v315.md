# v315 — Verified PostgreSQL backup and restore rehearsal

V315_VERIFIED_POSTGRES_BACKUP_RESTORE_REHEARSAL=1

## Purpose

V315 records the operator-run rehearsal that combines the guarded PostgreSQL
backup foundation from v313 with the disposable restore foundation from v314.

The checkpoint proves that a newly created, checksum-verified PostgreSQL
plain-SQL backup can be restored into a separately created disposable database,
validated against the source, and then cleaned up without modifying the source
development database.

V315 is an audit and runbook checkpoint. It does not introduce an automatic
database lifecycle command.

## Safety boundary

The source development database is `classifieds_db`.

- `classifieds_db is never a restore target`.
- The disposable target must begin with `test_`.
- The source and target identifiers must be distinct and safely validated.
- The target must not exist before the rehearsal begins.
- The restore target must be created explicitly by the operator.
- The restore command must confirm the exact typed target name.
- No connection may exist to the target before cleanup.
- No Django migration may be applied to the source or target.
- No production or development restore is authorized.

Expected source evidence includes:

    source_database_modified=false
    development_migration_applied=false
    mutation_allowed=false

## Exact pending migration state

The source and restored target must both remain in `pre_apply` mode with this
exact pending plan:

    accounts.0016_emailverificationstate_v306
    listings.0024_notification_provider_outcomes_v307
    listings.0025_notification_delivery_retention_v308

The expected counts are:

    pending_target_count=3
    applied_target_count=0

## Operator rehearsal sequence

Run all commands from the repository root.

### 1. Create a verified backup

    bash scripts/backup_postgres.sh --confirm

The operator may also pass the explicit source database and database user:

    bash scripts/backup_postgres.sh       --confirm       --source-db classifieds_db       --db-user postgres

The backup foundation must report:

    backup_gzip_integrity=verified
    backup_dump_identity=postgresql_plain_sql
    backup_checksum=verified
    backup_publish=atomic

Pre-existing backup artifacts remain unchanged.

### 2. Create the disposable target

The target must be absent before creation.

    docker compose exec -T db       psql       --no-psqlrc       --no-password       -X       -v ON_ERROR_STOP=1       -U postgres       -d postgres       -c 'CREATE DATABASE "test_restore_v315" TEMPLATE template0;'

### 3. Restore only into the disposable target

    bash scripts/restore_postgres.sh       --backup backups/postgres_YYYYMMDD_HHMMSS.sql.gz       --checksum backups/postgres_YYYYMMDD_HHMMSS.sql.gz.sha256       --target-db test_restore_v315       --confirm-target test_restore_v315       --source-db classifieds_db       --db-user postgres       --admin-db postgres

The restore must remain one transaction and must report:

    restore_target_disposable=verified
    restore_target_identity=verified
    restore_target_initially_empty=verified
    restore_transaction=single
    restore_performed=true
    source_database_modified=false
    migration_apply_performed=false

### 4. Check both databases

Run Django system checks independently against the source and target:

    docker compose exec -T       -e DB_NAME=classifieds_db       web       python manage.py check

    docker compose exec -T       -e DB_NAME=test_restore_v315       web       python manage.py check

Both checks must complete without issues.

### 5. Verify semantic equivalence

A successful rehearsal proves all of the following:

- Table inventories are equal.
- Per-table row counts are equal.
- Django migration histories are equal.
- Sequence values are equal.
- Logical column definitions are equal.
- CHECK-constraint truth tables are equal.
- Source and target migration preflights are both exact and read-only.
- The source database remains equal to its recorded pre-rehearsal baseline.

Plain `pg_dump --schema-only` text is not treated as the only equivalence
criterion. PostgreSQL can preserve physical PostgreSQL attnum history in the
source while a plain-SQL restore creates compact physical positions. PostgreSQL
deparser formatting can also represent equivalent casts differently after
restore.

Those differences may be accepted only after logical column equality,
row-count equality, migration-history equality, sequence equality, and
constraint-behaviour equality have all been established.

The final evidence must report:

    restore_semantically_equivalent=true

## Cleanup contract

Before cleanup:

    target_active_connections_before=0

The source database must still exist before cleanup.

Only the recorded `test_` target may be dropped.

    docker compose exec -T db       psql       --no-psqlrc       --no-password       -X       -v ON_ERROR_STOP=1       -U postgres       -d postgres       -c 'DROP DATABASE "test_restore_v315";'

Cleanup evidence must report:

    target_cleanup_performed=true
    target_exists_after=false
    source_unchanged=true
    backup_deleted=false
    development_migration_applied=false

The verified backup and checksum remain retained after target cleanup.

## Evidence retention

Environment-specific rehearsal evidence may be stored under `.git/` during the
local checkpoint workflow. Verified backup artifacts remain under the ignored
`backups/` directory.

Neither location is added to the tracked checkpoint.

The tracked documentation records the reproducible contract rather than local
database credentials, environment-specific paths, or the backup payload.

## Scope

V315 adds no model or migration file.

V315 adds no automatic startup operation.

V315 does not authorize a development or production restore.

V315 does not authorize migration application.

The tracked checkpoint contains no backup artifact.

The tracked checkpoint contains no database credentials.

The candidate scope is limited to:

- `backend/listings/test_verified_postgres_backup_restore_rehearsal_v315.py`
- `docs/verified_postgres_backup_restore_rehearsal_v315.md`
- `README_BACKUPS.md`
