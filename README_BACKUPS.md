# Backups

Run backup and restore commands from the repository root.

## PostgreSQL backup

Create a verified PostgreSQL backup and SHA-256 sidecar:

    bash scripts/backup_postgres.sh --confirm

Optional explicit database values:

    bash scripts/backup_postgres.sh \
      --confirm \
      --source-db classifieds_db \
      --db-user postgres

A successful run creates:

    backups/postgres_YYYYMMDD_HHMMSS.sql.gz
    backups/postgres_YYYYMMDD_HHMMSS.sql.gz.sha256

The command verifies:

- the `pg_dump` and gzip pipeline;
- gzip integrity;
- PostgreSQL plain-SQL dump identity;
- the SHA-256 sidecar;
- atomic final artifact publication.

Existing files are never overwritten. Partial artifacts are removed on failure.

## Disposable PostgreSQL restore

Restore is limited to a separately prepared disposable database whose name
begins with `test_`.

Example:

    bash scripts/restore_postgres.sh \
      --backup backups/postgres_YYYYMMDD_HHMMSS.sql.gz \
      --target-db test_restore_rehearsal \
      --confirm-target test_restore_rehearsal \
      --source-db classifieds_db

The restore command:

- verifies the backup and adjacent SHA-256 sidecar;
- requires typed confirmation of the exact target;
- refuses development, source, administrative, and non-`test_` targets;
- requires an existing target with zero active connections;
- requires zero non-system tables before restore;
- executes the SQL stream with one transaction and stop-on-error behavior;
- never creates, removes, force-disconnects, or empties a database;
- never applies Django migrations.

A production or development restore requires a separate procedure and explicit
human authorization. This disposable-target command does not provide it.

## Verified PostgreSQL backup and restore rehearsal

V315 combines the guarded backup and disposable restore foundations into an
explicit operator-run rehearsal.

The rehearsal must:

- create a new verified PostgreSQL backup and adjacent SHA-256 sidecar;
- restore only into a separately created `test_` database;
- compare table inventories, row counts, migration history, sequences, logical
  columns, and relevant CHECK-constraint behaviour;
- confirm that the source development database remains unchanged;
- confirm that the exact three notification-delivery migrations remain
  unapplied;
- remove the disposable target after verification;
- retain the verified backup and checksum for the later migration rollout.

The rehearsal does not authorize migration application or a development or
production restore.

The disposable target must be removed after verification. The backup pair must
remain under the ignored `backups/` directory.

See `docs/verified_postgres_backup_restore_rehearsal_v315.md` for the full
operator sequence and evidence contract.

## Media backup

Create a media backup:

    bash scripts/backup_media.sh

## Media restore

Restore media:

    bash scripts/restore_media.sh \
      backups/media_YYYYMMDD_HHMMSS.tar.gz

## Operational notes

- Backup artifacts are stored under `backups/`.
- The `backups/` directory is excluded from Git.
- Copy verified backups and checksum sidecars off the server regularly.
- Production deployments should also use server-level or managed-database
  backup facilities.
- Backup creation never authorizes a migration or database restore.
- Disposable restore rehearsal never authorizes a production restore.
