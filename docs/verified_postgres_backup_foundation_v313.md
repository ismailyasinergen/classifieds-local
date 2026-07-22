# v313 — Verified PostgreSQL backup foundation

## Purpose

V313 replaces the legacy one-line PostgreSQL backup path with a guarded,
verified, and atomically published backup workflow.

The resulting artifact pair is compatible with the v312 rollout-authorization
evidence gate:

- `backups/postgres_YYYYMMDD_HHMMSS.sql.gz`
- `backups/postgres_YYYYMMDD_HHMMSS.sql.gz.sha256`

V313 creates backups only. It never restores a database or applies migrations.

## Command

Run from the repository root:

    bash scripts/backup_postgres.sh --confirm

Optional explicit values:

    bash scripts/backup_postgres.sh \
      --confirm \
      --source-db classifieds_db \
      --db-user postgres

`--timestamp YYYYMMDD_HHMMSS` exists for deterministic testing and controlled
operator workflows. Normal use should omit it.

## Safety contract

The command:

- requires explicit `--confirm`;
- validates the database and role identifiers;
- refuses to overwrite an existing backup or checksum;
- writes into `backups/`, which remains excluded by `.gitignore`;
- enables shell pipeline failure propagation;
- writes the dump to a private temporary file;
- requires a non-empty artifact;
- verifies gzip integrity;
- verifies the PostgreSQL plain-SQL dump header;
- creates a SHA-256 checksum sidecar;
- rereads and verifies the sidecar;
- removes partial and incompletely published artifacts on failure;
- publishes the backup and checksum with final-name renames;
- reports stable evidence markers.

The script never calls `pg_restore`, `psql`, Django migration commands,
`createdb`, `dropdb`, forced database termination, or restore tooling.

## Artifact verification

A successful run reports:

    backup_gzip_integrity=verified
    backup_dump_identity=postgresql_plain_sql
    backup_checksum=verified
    backup_publish=atomic
    backup_restore_performed=false
    migration_apply_performed=false

The adjacent sidecar contains one lowercase SHA-256 digest and the exact backup
filename.

## Legacy artifacts

Existing backup files without a matching `.sha256` sidecar are not accepted by
the v312 rollout-authorization gate.

A zero-byte media archive or an unusually small legacy database artifact must
not be treated as verified merely because it exists. Verification requires the
current command or an independently reviewed equivalent process.

## Scope

V313 adds no model, migration file, route, view, template, background worker,
database restore, migration application, schema mutation, or application-data
mutation.
