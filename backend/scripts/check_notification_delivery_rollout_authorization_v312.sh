#!/usr/bin/env bash

set -Eeuo pipefail

V312_NOTIFICATION_DELIVERY_MIGRATION_ROLLOUT_AUTHORIZATION=1

source_db="${SOURCE_DB:-classifieds_db}"
backup_path=""
checksum_path=""
expected_head=""
max_age_hours="24"
confirmed=0

v311_tag=(
  "project-checkpoint-v311-notification-delivery-"
  "migration-rollout-rehearsal"
)

v311_tag="${v311_tag[*]}"
v311_tag="${v311_tag// /}"

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/check_notification_delivery_rollout_authorization_v312.sh \
    --confirm-check \
    --backup backups/postgres_YYYYMMDD_HHMMSS.sql.gz \
    --expected-head COMMIT_SHA \
    [--checksum BACKUP.sha256] \
    [--source-db DATABASE] \
    [--max-age-hours HOURS]

This command is read-only.

It verifies:
  - an explicit operator check request;
  - a repository-local PostgreSQL backup artifact;
  - an adjacent SHA-256 checksum sidecar;
  - gzip integrity and PostgreSQL plain-SQL dump identity;
  - backup freshness;
  - exact clean Git synchronization;
  - the completed v311 rehearsal checkpoint;
  - the v310 ready_to_apply migration contract.

It never creates, restores, applies, reverses, or removes migrations.
It does not grant migration authorization.
USAGE
}

usage_error() {
  printf 'ERROR: %s\n\n' "$1" >&2
  usage >&2
  exit 2
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --confirm-check)
      confirmed=1
      shift
      ;;
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
    --expected-head)
      [ "$#" -ge 2 ] || usage_error \
        "--expected-head requires a value"
      expected_head="$2"
      shift 2
      ;;
    --expected-head=*)
      expected_head="${1#*=}"
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
    --max-age-hours)
      [ "$#" -ge 2 ] || usage_error \
        "--max-age-hours requires a value"
      max_age_hours="$2"
      shift 2
      ;;
    --max-age-hours=*)
      max_age_hours="${1#*=}"
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
    "explicit --confirm-check authorization is required"
fi

if [ -z "$backup_path" ]; then
  usage_error \
    "--backup is required"
fi

if [ -z "$checksum_path" ]; then
  checksum_path="${backup_path}.sha256"
fi

if [ -z "$expected_head" ]; then
  usage_error \
    "--expected-head is required"
fi

if [[ ! "$source_db" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
  usage_error \
    "source database name is not a safe PostgreSQL identifier"
fi

if [[ ! "$expected_head" =~ ^[0-9a-f]{40}$ ]]; then
  usage_error \
    "expected head must be a lowercase 40-character commit SHA"
fi

if [[ ! "$max_age_hours" =~ ^[1-9][0-9]*$ ]]; then
  usage_error \
    "max age hours must be a positive integer"
fi

if [ ! -f docker-compose.yml ]; then
  usage_error \
    "run the authorization check from the repository root"
fi

if [ ! -f backend/manage.py ]; then
  usage_error \
    "backend/manage.py is missing"
fi

printf '\n===== V312 BACKUP ARTIFACT CONTRACT =====\n'

BACKUP_PATH="$backup_path" \
CHECKSUM_PATH="$checksum_path" \
MAX_AGE_HOURS="$max_age_hours" \
python - <<'PY'
from __future__ import annotations

from pathlib import Path
import gzip
import hashlib
import os
import re
import sys
import time

repository_root = Path.cwd().resolve()
backup_root = (
    repository_root / "backups"
).resolve()

backup_candidate = Path(
    os.environ["BACKUP_PATH"]
)

checksum_candidate = Path(
    os.environ["CHECKSUM_PATH"]
)

max_age_hours = int(
    os.environ["MAX_AGE_HOURS"]
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
    checksum_lines = [
        line.strip()
        for line in checksum.read_text(
            encoding="utf-8",
            errors="strict",
        ).splitlines()
        if line.strip()
    ]

    if len(checksum_lines) != 1:
        errors.append(
            "checksum sidecar must contain exactly one non-empty line"
        )
    else:
        expected_digest = (
            checksum_lines[0].split()[0].lower()
        )

        if not re.fullmatch(
            r"[0-9a-f]{64}",
            expected_digest,
        ):
            errors.append(
                "checksum sidecar does not begin with a valid SHA-256 digest"
            )
        else:
            digest = hashlib.sha256()

            with backup.open("rb") as stream:
                while True:
                    chunk = stream.read(
                        1024 * 1024
                    )

                    if not chunk:
                        break

                    digest.update(chunk)

            observed_digest = digest.hexdigest()

            if observed_digest != expected_digest:
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
        OSError,
        EOFError,
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

    now = time.time()
    age_seconds = (
        now - backup.stat().st_mtime
    )

    if age_seconds < -300:
        errors.append(
            "backup modification time is unexpectedly in the future"
        )
    elif age_seconds > (
        max_age_hours * 3600
    ):
        errors.append(
            "backup is older than the allowed freshness window"
        )

if errors:
    print(
        "ERROR: backup artifact contract failed."
    )

    for error in errors:
        print("-", error)

    sys.exit(1)

age_hours = max(
    0.0,
    (
        time.time()
        - backup.stat().st_mtime
    )
    / 3600,
)

print(f"backup_file={backup}")
print(f"checksum_file={checksum}")
print(f"backup_size_bytes={backup.stat().st_size}")
print(f"backup_age_hours={age_hours:.3f}")
print("backup_checksum=verified")
print("backup_gzip_integrity=verified")
print("backup_dump_identity=postgresql_plain_sql")
PY

printf '\n===== V312 GIT AUTHORIZATION CONTRACT =====\n'

EXPECTED_HEAD="$expected_head" \
V311_TAG="$v311_tag" \
python - <<'PY'
import os
import subprocess
import sys

expected_head = os.environ["EXPECTED_HEAD"]
v311_tag = os.environ["V311_TAG"]


def output(args):
    return subprocess.check_output(
        args,
        text=True,
        encoding="utf-8",
        errors="strict",
    ).strip()


branch = output(
    ["git", "branch", "--show-current"]
)

references = {
    "HEAD": output(
        ["git", "rev-parse", "HEAD"]
    ),
    "main": output(
        ["git", "rev-parse", "main"]
    ),
    "origin/main": output(
        ["git", "rev-parse", "origin/main"]
    ),
}

status = output(
    ["git", "status", "--porcelain=v1"]
)

tag_type = output(
    ["git", "cat-file", "-t", v311_tag]
)

tag_commit = output(
    ["git", "rev-parse", f"{v311_tag}^{{}}"]
)

ancestor = subprocess.run(
    [
        "git",
        "merge-base",
        "--is-ancestor",
        tag_commit,
        expected_head,
    ],
    check=False,
)

errors = []

if branch != "main":
    errors.append(
        f"current branch is not main: {branch}"
    )

for label, value in references.items():
    if value != expected_head:
        errors.append(
            f"{label} does not match the expected head: {value}"
        )

if status:
    errors.append(
        "working tree is not clean: "
        + status.replace("\n", "; ")
    )

if tag_type != "tag":
    errors.append(
        f"v311 rehearsal checkpoint is not annotated: {tag_type}"
    )

if ancestor.returncode != 0:
    errors.append(
        "v311 rehearsal checkpoint is not an ancestor "
        "of the expected rollout commit"
    )

if errors:
    print(
        "ERROR: Git authorization contract failed."
    )

    for error in errors:
        print("-", error)

    sys.exit(1)

print(f"rollout_branch={branch}")
print(f"rollout_commit={expected_head}")
print(f"rehearsal_tag={v311_tag}")
print(f"rehearsal_commit={tag_commit}")
print("repository_sync=verified")
print("working_tree=clean")
print("rehearsal_ancestry=verified")
PY

printf '\n===== V312 DATABASE READ-ONLY PREFLIGHT =====\n'

source_preflight="$(
  docker compose exec -T \
    -e DB_NAME="$source_db" \
    -e PYTHONDONTWRITEBYTECODE=1 \
    web \
    python manage.py \
    check_notification_delivery_migration_rollout \
    --json
)"

printf '%s\n' "$source_preflight"

PREFLIGHT_JSON="$source_preflight" \
python - <<'PY'
import json
import os
import sys

result = json.loads(
    os.environ["PREFLIGHT_JSON"]
)

expected_plan = [
    "accounts.0016_emailverificationstate_v306",
    "listings.0024_notification_provider_outcomes_v307",
    "listings.0025_notification_delivery_retention_v308",
]

errors = []

if result.get("status") != "ready_to_apply":
    errors.append(
        f"unexpected status: {result.get('status')!r}"
    )

if result.get("migration_mode") != "pre_apply":
    errors.append(
        "database is not in pre_apply mode"
    )

if result.get("pending_plan") != expected_plan:
    errors.append(
        "pending migration plan is not exact"
    )

if result.get("pending_target_count") != 3:
    errors.append(
        "expected exactly three pending target migrations"
    )

if result.get("applied_target_count") != 0:
    errors.append(
        "one or more target migrations are already applied"
    )

if result.get("blocking_not_ready_count") != 0:
    errors.append(
        "blocking rollout checks remain"
    )

if result.get("auth_users_without_email") != 0:
    errors.append(
        "one or more users have no email address"
    )

if result.get("read_only") is not True:
    errors.append(
        "v310 preflight is not read-only"
    )

if result.get("mutation_allowed") is not False:
    errors.append(
        "v310 preflight unexpectedly allows mutation"
    )

if errors:
    print(
        "ERROR: database authorization contract failed."
    )

    for error in errors:
        print("-", error)

    sys.exit(1)

print("database_status=ready_to_apply")
print("migration_mode=pre_apply")
print("pending_target_count=3")
print("applied_target_count=0")
print("users_without_email=0")
print("database_preflight=read_only")
PY

printf '\n===== V312 AUTHORIZATION RESULT =====\n'
echo "authorization_status=ready_for_explicit_human_approval"
echo "mutation_allowed=false"
echo "migration_apply_performed=false"
echo "backup_restore_performed=false"
echo "This command did not grant or execute migration authorization."
