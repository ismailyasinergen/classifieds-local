# v314 — Verified PostgreSQL restore foundation

## Purpose

V314 replaces the legacy Enter-prompt restore command with a narrowly scoped
restore workflow for a pre-created disposable PostgreSQL target.

It consumes the verified artifact pair produced by v313:

- `backups/postgres_YYYYMMDD_HHMMSS.sql.gz`
- `backups/postgres_YYYYMMDD_HHMMSS.sql.gz.sha256`

V314 does not restore into the development database. The target must begin
with `test_`, already exist, contain no user tables, and have no active
connections.

## Command

Example against an explicitly prepared disposable target:

    bash scripts/restore_postgres.sh \
      --backup backups/postgres_YYYYMMDD_HHMMSS.sql.gz \
      --target-db test_restore_rehearsal \
      --confirm-target test_restore_rehearsal \
      --source-db classifieds_db

The value supplied to `--confirm-target` must exactly match `--target-db`.

## Artifact verification

Before connecting to the target, the command verifies:

- both files are regular non-symlink files inside `backups/`;
- the backup filename matches the expected timestamp pattern;
- the sidecar contains one SHA-256 digest and the exact backup filename;
- the digest matches the compressed backup;
- gzip decoding succeeds;
- the dump identifies as PostgreSQL plain SQL.

## Target guardrails

The command refuses to proceed unless:

- all database and role values are safe identifiers;
- the target begins with `test_`;
- source, target, and administrative databases are distinct;
- the target already exists;
- the connected database identity equals the typed target;
- the target has zero active connections;
- the target contains zero non-system tables.

It does not create, remove, rename, disconnect, or empty a database.

## Restore transaction

The verified plain-SQL stream is sent only to the typed disposable target with:

    --single-transaction
    -v ON_ERROR_STOP=1

A statement failure therefore returns a nonzero status and requests rollback of
the restore transaction instead of reporting success after a partial script.

## Success evidence

A successful disposable restore reports:

    restore_target_disposable=verified
    restore_target_identity=verified
    restore_target_initially_empty=verified
    restore_transaction=single
    backup_checksum=verified
    backup_gzip_integrity=verified
    backup_dump_identity=postgresql_plain_sql
    restore_performed=true
    source_database_modified=false
    migration_apply_performed=false

## Scope

V314 adds no model, migration file, route, view, template, startup operation,
database lifecycle automation, forced connection termination, production
restore authorization, development-database restore, or migration application.
