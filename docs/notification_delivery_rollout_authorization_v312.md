# v312 — Notification delivery rollout authorization

## Purpose

V312 adds a fail-closed, read-only authorization evidence gate for the three
notification-delivery migrations rehearsed in v311:

1. `accounts.0016_emailverificationstate_v306`
2. `listings.0024_notification_provider_outcomes_v307`
3. `listings.0025_notification_delivery_retention_v308`

The gate does not apply, reverse, restore, create, clone, or remove a database.

It does not grant migration authorization. It reports whether the technical
evidence is ready for a separate explicit human approval decision.

## Command

A current PostgreSQL plain-SQL gzip backup and SHA-256 sidecar are required.

Example checksum creation:

    sha256sum backups/postgres_YYYYMMDD_HHMMSS.sql.gz \
      > backups/postgres_YYYYMMDD_HHMMSS.sql.gz.sha256

Read-only authorization check:

    bash scripts/check_notification_delivery_rollout_authorization_v312.sh \
      --confirm-check \
      --backup backups/postgres_YYYYMMDD_HHMMSS.sql.gz \
      --expected-head "$(git rev-parse HEAD)"

Optional arguments:

    --checksum backups/postgres_YYYYMMDD_HHMMSS.sql.gz.sha256
    --source-db classifieds_db
    --max-age-hours 24

## Backup evidence contract

The supplied backup must:

- be a regular file inside the repository `backups/` directory;
- not be a symbolic link;
- match `postgres_YYYYMMDD_HHMMSS.sql.gz`;
- have a matching checksum sidecar inside `backups/`;
- contain exactly one valid SHA-256 digest line;
- match the recorded SHA-256 digest;
- pass gzip decoding;
- identify as a PostgreSQL plain-SQL dump;
- be newer than the configured freshness window.

The check reads the backup header and digest only. It never restores the backup.

## Git evidence contract

The operator must supply an exact lowercase 40-character expected commit SHA.

The check requires:

- the current branch to be `main`;
- `HEAD`, `main`, and `origin/main` to match the supplied commit;
- a clean working tree;
- the annotated v311 rehearsal checkpoint tag;
- the v311 rehearsal commit to be an ancestor of the supplied rollout commit.

## Database evidence contract

The script runs the v310 read-only preflight and requires:

- `status=ready_to_apply`;
- `migration_mode=pre_apply`;
- the exact three-migration pending plan;
- three pending target migrations;
- zero applied target migrations;
- zero blocking checks;
- zero users without an email address;
- `read_only=true`;
- `mutation_allowed=false`.

## Result meaning

Success reports:

    authorization_status=ready_for_explicit_human_approval
    mutation_allowed=false
    migration_apply_performed=false
    backup_restore_performed=false

This means the technical evidence is ready for review. It does not mean the
development or production database may be migrated without a later explicit
operator instruction.

## Existing backup and restore scripts

The legacy `scripts/backup_postgres.sh` creates a gzip-compressed plain-SQL
backup but does not currently generate a checksum sidecar.

The legacy `scripts/restore_postgres.sh` writes directly into its configured
target database after an interactive Enter prompt. V312 does not invoke or
modify that restore path.

A restore must remain a separately reviewed procedure against a disposable or
explicitly authorized target database.

## Scope

V312 adds no model, migration file, route, view, template, startup migration,
backup creation, database restore, migration apply, migration reversal, or
application-data mutation.
