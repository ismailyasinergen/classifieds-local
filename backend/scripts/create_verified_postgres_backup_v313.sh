#!/usr/bin/env bash

set -Eeuo pipefail

V313_VERIFIED_POSTGRES_BACKUP_FOUNDATION=1

source_db="${SOURCE_DB:-${POSTGRES_DB:-classifieds_db}}"
db_user="${DB_USER:-${POSTGRES_USER:-postgres}}"
timestamp=""
confirmed=0

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/backup_postgres.sh \
    --confirm \
    [--source-db DATABASE] \
    [--db-user USER] \
    [--timestamp YYYYMMDD_HHMMSS]

The command creates:

  backups/postgres_YYYYMMDD_HHMMSS.sql.gz
  backups/postgres_YYYYMMDD_HHMMSS.sql.gz.sha256

Safety properties:

  - explicit --confirm is required;
  - PostgreSQL identifiers are validated;
  - existing output files are never overwritten;
  - pg_dump and gzip failures are detected;
  - gzip integrity and PostgreSQL dump identity are verified;
  - a SHA-256 sidecar is generated and reverified;
  - partial files are removed on failure;
  - final artifacts are published with atomic renames.

The command creates a backup only. It never restores a database,
applies migrations, or modifies application data.
USAGE
}

usage_error() {
  printf 'ERROR: %s\n\n' "$1" >&2
  usage >&2
  exit 2
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --confirm)
      confirmed=1
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
    --timestamp)
      [ "$#" -ge 2 ] || usage_error \
        "--timestamp requires a value"
      timestamp="$2"
      shift 2
      ;;
    --timestamp=*)
      timestamp="${1#*=}"
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

if [ "$confirmed" -ne 1 ]; then
  usage_error \
    "explicit --confirm authorization is required"
fi

if [[ ! "$source_db" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
  usage_error \
    "source database name is not a safe PostgreSQL identifier"
fi

if [[ ! "$db_user" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
  usage_error \
    "database user is not a safe PostgreSQL identifier"
fi

if [ -z "$timestamp" ]; then
  timestamp="$(
    date +"%Y%m%d_%H%M%S"
  )"
fi

if [[ ! "$timestamp" =~ ^[0-9]{8}_[0-9]{6}$ ]]; then
  usage_error \
    "timestamp must match YYYYMMDD_HHMMSS"
fi

if [ ! -f docker-compose.yml ]; then
  usage_error \
    "run the backup command from the repository root"
fi

backup_root="backups"
backup_name="postgres_${timestamp}.sql.gz"
checksum_name="${backup_name}.sha256"

final_backup="${backup_root}/${backup_name}"
final_checksum="${backup_root}/${checksum_name}"

temporary_backup="${final_backup}.partial.$$"
temporary_checksum="${final_checksum}.partial.$$"

mkdir -p "$backup_root"

if [ -e "$final_backup" ]; then
  usage_error \
    "backup artifact already exists: $final_backup"
fi

if [ -e "$final_checksum" ]; then
  usage_error \
    "checksum artifact already exists: $final_checksum"
fi

if [ -e "$temporary_backup" ]; then
  usage_error \
    "temporary backup path already exists"
fi

if [ -e "$temporary_checksum" ]; then
  usage_error \
    "temporary checksum path already exists"
fi

umask 077

published=0

cleanup() {
  original_status=$?

  trap - EXIT

  rm -f \
    "$temporary_backup" \
    "$temporary_checksum"

  if [ "$published" -ne 1 ]; then
    rm -f \
      "$final_backup" \
      "$final_checksum"
  fi

  exit "$original_status"
}

trap cleanup EXIT

printf '\n===== CREATE POSTGRESQL PLAIN-SQL BACKUP =====\n'
printf 'source_database=%s\n' "$source_db"
printf 'database_user=%s\n' "$db_user"
printf 'target_backup=%s\n' "$final_backup"

docker compose exec -T \
  db \
  pg_dump \
  --format=plain \
  --no-owner \
  --no-privileges \
  --no-password \
  -U "$db_user" \
  "$source_db" |
  gzip -c \
    > "$temporary_backup"

if [ ! -s "$temporary_backup" ]; then
  echo "ERROR: generated backup is empty." >&2
  exit 1
fi

printf '\n===== VERIFY GZIP INTEGRITY =====\n'

gzip -t "$temporary_backup"

printf '\n===== VERIFY POSTGRESQL DUMP IDENTITY =====\n'

BACKUP_PATH="$temporary_backup" \
python - <<'PY'
from pathlib import Path
import gzip
import os
import sys

backup = Path(
    os.environ["BACKUP_PATH"]
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
    print(
        "ERROR: gzip verification failed: "
        f"{type(exc).__name__}",
        file=sys.stderr,
    )
    sys.exit(1)

if b"PostgreSQL database dump" not in header:
    print(
        "ERROR: artifact does not identify as a "
        "PostgreSQL plain-SQL dump.",
        file=sys.stderr,
    )
    sys.exit(1)

print("backup_dump_identity=postgresql_plain_sql")
PY

printf '\n===== CREATE SHA-256 SIDECAR =====\n'

BACKUP_PATH="$temporary_backup" \
CHECKSUM_PATH="$temporary_checksum" \
BACKUP_NAME="$backup_name" \
python - <<'PY'
from pathlib import Path
import hashlib
import os

backup = Path(
    os.environ["BACKUP_PATH"]
)

checksum = Path(
    os.environ["CHECKSUM_PATH"]
)

backup_name = os.environ["BACKUP_NAME"]

digest = hashlib.sha256()

with backup.open("rb") as stream:
    while True:
        chunk = stream.read(
            1024 * 1024
        )

        if not chunk:
            break

        digest.update(chunk)

checksum.write_text(
    f"{digest.hexdigest()}  {backup_name}\n",
    encoding="utf-8",
    newline="\n",
)
PY

printf '\n===== REVERIFY SHA-256 SIDECAR =====\n'

BACKUP_PATH="$temporary_backup" \
CHECKSUM_PATH="$temporary_checksum" \
BACKUP_NAME="$backup_name" \
python - <<'PY'
from pathlib import Path
import hashlib
import os
import re
import sys

backup = Path(
    os.environ["BACKUP_PATH"]
)

checksum = Path(
    os.environ["CHECKSUM_PATH"]
)

backup_name = os.environ["BACKUP_NAME"]

lines = [
    line.strip()
    for line in checksum.read_text(
        encoding="utf-8",
        errors="strict",
    ).splitlines()
    if line.strip()
]

errors = []

if len(lines) != 1:
    errors.append(
        "checksum sidecar must contain exactly one line"
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
            r"[0-9a-f]{64}",
            expected_digest,
        ):
            errors.append(
                "checksum sidecar digest is invalid"
            )

        if recorded_name != backup_name:
            errors.append(
                "checksum sidecar filename is invalid"
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

        if digest.hexdigest() != expected_digest:
            errors.append(
                "checksum sidecar does not match the backup"
            )

if errors:
    print(
        "ERROR: checksum verification failed.",
        file=sys.stderr,
    )

    for error in errors:
        print(
            f"- {error}",
            file=sys.stderr,
        )

    sys.exit(1)

print("backup_checksum=verified")
PY

printf '\n===== ATOMICALLY PUBLISH VERIFIED ARTIFACTS =====\n'

mv \
  "$temporary_backup" \
  "$final_backup"

mv \
  "$temporary_checksum" \
  "$final_checksum"

published=1
trap - EXIT

printf 'backup_file=%s\n' "$final_backup"
printf 'checksum_file=%s\n' "$final_checksum"
printf 'backup_size_bytes=%s\n' "$(
  wc -c < "$final_backup" |
  tr -d '[:space:]'
)"
echo "backup_gzip_integrity=verified"
echo "backup_dump_identity=postgresql_plain_sql"
echo "backup_checksum=verified"
echo "backup_publish=atomic"
echo "backup_restore_performed=false"
echo "migration_apply_performed=false"
