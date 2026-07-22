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

## Media backup

Create a media backup:

    bash scripts/backup_media.sh

## Database restore

Restore remains a separate, destructive operator workflow:

    bash scripts/restore_postgres.sh \
      backups/postgres_YYYYMMDD_HHMMSS.sql.gz

Do not restore merely because a file exists. Verify the matching SHA-256
sidecar and review the target database before any restore.

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
