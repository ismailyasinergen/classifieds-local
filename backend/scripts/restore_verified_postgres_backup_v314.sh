#!/usr/bin/env bash

set -Eeuo pipefail

V314_VERIFIED_POSTGRES_RESTORE_FOUNDATION=1

backup_path=""
checksum_path=""
target_db=""
confirmed_target=""

source_db="${SOURCE_DB:-${POSTGRES_DB:-classifieds_db}}"
db_user="${DB_USER:-${POSTGRES_USER:-postgres}}"
admin_db="${ADMIN_DB:-postgres}"

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/restore_postgres.sh \
    --backup backups/postgres_YYYYMMDD_HHMMSS.sql.gz \
    --target-db test_DATABASE \
    --confirm-target test_DATABASE \
    [--checksum BACKUP.sha256] \
    [--source-db DATABASE] \
    [--db-user USER] \
    [--admin-db DATABASE]

Safety contract:

  - the target must already exist;
  - the target must begin with test_;
  - typed confirmation must exactly match the target;
  - source and target databases must differ;
  - the verified backup and SHA-256 sidecar must be inside backups/;
  - gzip integrity and PostgreSQL plain-SQL identity are checked;
  - the target must have zero active connections;
  - the target must contain no non-system tables;
  - the restore runs in one database transaction;
  - no database is created, removed, renamed, or force-disconnected;
  - no Django migration command is executed.

This is a destructive operation against the explicitly named disposable target.
USAGE
}

usage_error() {
  printf 'ERROR: %s\n\n' "$1" >&2
  usage >&2
  exit 2
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --backup)
      [ "$#" -ge 2 ] || usage_error \
        "--backup requires a value"
      backup_path="$2"
      shift 2
      ;;
    --backup=*)
      backup_path="${1#*=}"
      shift
      ;;
    --checksum)
      [ "$#" -ge 2 ] || usage_error \
        "--checksum requires a value"
      checksum_path="$2"
      shift 2
      ;;
    --checksum=*)
      checksum_path="${1#*=}"
      shift
      ;;
    --target-db)
      [ "$#" -ge 2 ] || usage_error \
        "--target-db requires a value"
      target_db="$2"
      shift 2
      ;;
    --target-db=*)
      target_db="${1#*=}"
      shift
      ;;
    --confirm-target)
      [ "$#" -ge 2 ] || usage_error \
        "--confirm-target requires a value"
      confirmed_target="$2"
      shift 2
      ;;
    --confirm-target=*)
      confirmed_target="${1#*=}"
      shift
      ;;
    --source-db)
      [ "$#" -ge 2 ] || usage_error \
        "--source-db requires a value"
      source_db="$2"
      shift 2
      ;;
    --source-db=*)
      source_db="${1#*=}"
      shift
      ;;
    --db-user)
      [ "$#" -ge 2 ] || usage_error \
        "--db-user requires a value"
      db_user="$2"
      shift 2
      ;;
    --db-user=*)
      db_user="${1#*=}"
      shift
      ;;
    --admin-db)
      [ "$#" -ge 2 ] || usage_error \
        "--admin-db requires a value"
      admin_db="$2"
      shift 2
      ;;
    --admin-db=*)
      admin_db="${1#*=}"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage_error "unknown argument: $1"
      ;;
  esac
done

if [ -z "$backup_path" ]; then
  usage_error \
    "--backup is required"
fi

if [ -z "$checksum_path" ]; then
  checksum_path="${backup_path}.sha256"
fi

if [ -z "$target_db" ]; then
  usage_error \
    "--target-db is required"
fi

if [ -z "$confirmed_target" ]; then
  usage_error \
    "explicit --confirm-target authorization is required"
fi

if [ "$confirmed_target" != "$target_db" ]; then
  usage_error \
    "typed target confirmation does not match --target-db"
fi

for identifier_name in \
  source_db \
  target_db \
  db_user \
  admin_db
do
  identifier_value="${!identifier_name}"

  if [[ ! "$identifier_value" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
    usage_error \
      "$identifier_name is not a safe PostgreSQL identifier"
  fi
done

if [[ ! "$target_db" =~ ^test_[a-zA-Z0-9_]+$ ]]; then
  usage_error \
    "target database must begin with test_"
fi

if [ "$target_db" = "$source_db" ]; then
  usage_error \
    "target database must differ from the source database"
fi

if [ "$target_db" = "$admin_db" ]; then
  usage_error \
    "target database must differ from the administrative database"
fi

if [ ! -f docker-compose.yml ]; then
  usage_error \
    "run the restore command from the repository root"
fi

printf '\n===== VERIFY BACKUP ARTIFACT CONTRACT =====\n'

BACKUP_PATH="$backup_path" \
CHECKSUM_PATH="$checksum_path" \
python - <<'PY'
from pathlib import Path
import gzip
import hashlib
import os
import re
import sys

repository_root = Path.cwd().resolve(
    strict=True
)

backup_root = (
    repository_root / "backups"
).resolve(
    strict=True
)

backup_candidate = Path(
    os.environ["BACKUP_PATH"]
)

checksum_candidate = Path(
    os.environ["CHECKSUM_PATH"]
)

errors = []

if backup_candidate.is_symlink():
    errors.append(
        "backup path must not be a symbolic link"
    )

if checksum_candidate.is_symlink():
    errors.append(
        "checksum path must not be a symbolic link"
    )

try:
    backup = backup_candidate.resolve(
        strict=True
    )
except FileNotFoundError:
    backup = None
    errors.append(
        f"backup file does not exist: {backup_candidate}"
    )

try:
    checksum = checksum_candidate.resolve(
        strict=True
    )
except FileNotFoundError:
    checksum = None
    errors.append(
        "checksum sidecar does not exist: "
        f"{checksum_candidate}"
    )

if backup is not None:
    try:
        backup.relative_to(
            backup_root
        )
    except ValueError:
        errors.append(
            "backup must be located inside the repository backups directory"
        )

    if not backup.is_file():
        errors.append(
            "backup path is not a regular file"
        )

    if not re.fullmatch(
        r"postgres_[0-9]{8}_[0-9]{6}\.sql\.gz",
        backup.name,
    ):
        errors.append(
            "backup filename must match "
            "postgres_YYYYMMDD_HHMMSS.sql.gz"
        )

    if backup.stat().st_size <= 0:
        errors.append(
            "backup file is empty"
        )

if checksum is not None:
    try:
        checksum.relative_to(
            backup_root
        )
    except ValueError:
        errors.append(
            "checksum must be located inside the repository backups directory"
        )

    if not checksum.is_file():
        errors.append(
            "checksum path is not a regular file"
        )

if (
    backup is not None
    and checksum is not None
    and backup.is_file()
    and checksum.is_file()
):
    lines = [
        line.strip()
        for line in checksum.read_text(
            encoding="utf-8",
            errors="strict",
        ).splitlines()
        if line.strip()
    ]

    if len(lines) != 1:
        errors.append(
            "checksum sidecar must contain exactly one non-empty line"
        )
    else:
        parts = lines[0].split()

        if len(parts) != 2:
            errors.append(
                "checksum sidecar format is invalid"
            )
        else:
            expected_digest, recorded_name = parts

            if not re.fullmatch(
                r"[0-9a-fA-F]{64}",
                expected_digest,
            ):
                errors.append(
                    "checksum sidecar does not begin with a valid SHA-256 digest"
                )

            if recorded_name != backup.name:
                errors.append(
                    "checksum sidecar filename does not match the backup"
                )

            digest = hashlib.sha256()

            with backup.open("rb") as stream:
                while True:
                    chunk = stream.read(
                        1024 * 1024
                    )

                    if not chunk:
                        break

                    digest.update(chunk)

            if digest.hexdigest() != expected_digest.lower():
                errors.append(
                    "backup SHA-256 checksum does not match"
                )

    try:
        with gzip.open(
            backup,
            "rb",
        ) as stream:
            header = stream.read(
                8192
            )
    except (
        EOFError,
        OSError,
    ) as exc:
        errors.append(
            "backup is not a valid gzip stream: "
            f"{type(exc).__name__}"
        )
    else:
        if (
            b"PostgreSQL database dump"
            not in header
        ):
            errors.append(
                "backup does not identify as a PostgreSQL plain-SQL dump"
            )

if errors:
    print(
        "ERROR: backup artifact contract failed.",
        file=sys.stderr,
    )

    for error in errors:
        print(
            f"- {error}",
            file=sys.stderr,
        )

    sys.exit(1)

print(f"backup_file={backup}")
print(f"checksum_file={checksum}")
print(f"backup_size_bytes={backup.stat().st_size}")
print("backup_checksum=verified")
print("backup_gzip_integrity=verified")
print("backup_dump_identity=postgresql_plain_sql")
PY

run_scalar_query() {
  query_database="$1"
  query_sql="$2"

  docker compose exec -T \
    db \
    psql \
    --no-psqlrc \
    --no-password \
    -X \
    -v ON_ERROR_STOP=1 \
    -U "$db_user" \
    -d "$query_database" \
    -Atqc "$query_sql"
}

printf '\n===== VERIFY DISPOSABLE TARGET EXISTS =====\n'

target_exists="$(
  run_scalar_query \
    "$admin_db" \
    "SELECT count(*) FROM pg_database WHERE datname = '$target_db';"
)"

if [ "$target_exists" != "1" ]; then
  echo \
    "ERROR: disposable target database does not exist: $target_db" \
    >&2
  exit 1
fi

printf '\n===== VERIFY TARGET IDENTITY =====\n'

target_identity="$(
  run_scalar_query \
    "$target_db" \
    "SELECT current_database();"
)"

if [ "$target_identity" != "$target_db" ]; then
  echo \
    "ERROR: connected target identity does not match --target-db" \
    >&2
  exit 1
fi

printf '\n===== VERIFY TARGET HAS NO ACTIVE CONNECTIONS =====\n'

active_connections="$(
  run_scalar_query \
    "$admin_db" \
    "SELECT count(*) FROM pg_stat_activity WHERE datname = '$target_db';"
)"

if ! [[ "$active_connections" =~ ^[0-9]+$ ]]; then
  echo \
    "ERROR: active connection count is not numeric" \
    >&2
  exit 1
fi

if [ "$active_connections" -ne 0 ]; then
  echo \
    "ERROR: disposable target has active connections: $active_connections" \
    >&2
  exit 1
fi

printf '\n===== VERIFY TARGET CONTAINS NO USER TABLES =====\n'

target_table_count="$(
  run_scalar_query \
    "$target_db" \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema');"
)"

if ! [[ "$target_table_count" =~ ^[0-9]+$ ]]; then
  echo \
    "ERROR: target table count is not numeric" \
    >&2
  exit 1
fi

if [ "$target_table_count" -ne 0 ]; then
  echo \
    "ERROR: disposable target is not empty: $target_table_count user tables" \
    >&2
  exit 1
fi

printf '\n===== RESTORE VERIFIED BACKUP INTO DISPOSABLE TARGET =====\n'
printf 'source_database=%s\n' "$source_db"
printf 'target_database=%s\n' "$target_db"
printf 'database_user=%s\n' "$db_user"

gzip -dc "$backup_path" |
  docker compose exec -T \
    db \
    psql \
    --no-psqlrc \
    --no-password \
    --single-transaction \
    -X \
    -v ON_ERROR_STOP=1 \
    -U "$db_user" \
    -d "$target_db"

printf '\n===== POST-RESTORE TARGET IDENTITY =====\n'

post_restore_identity="$(
  run_scalar_query \
    "$target_db" \
    "SELECT current_database();"
)"

if [ "$post_restore_identity" != "$target_db" ]; then
  echo \
    "ERROR: post-restore target identity mismatch" \
    >&2
  exit 1
fi

echo "restore_target_disposable=verified"
echo "restore_target_identity=verified"
echo "restore_target_initially_empty=verified"
echo "restore_transaction=single"
echo "backup_checksum=verified"
echo "backup_gzip_integrity=verified"
echo "backup_dump_identity=postgresql_plain_sql"
echo "restore_performed=true"
echo "source_database_modified=false"
echo "migration_apply_performed=false"
