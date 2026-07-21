#!/usr/bin/env bash

set -Eeuo pipefail

V311_NOTIFICATION_DELIVERY_MIGRATION_ROLLOUT_REHEARSAL=1

source_db="${SOURCE_DB:-classifieds_db}"
clone_name="${CLONE_NAME:-test_classifieds_v311_rehearsal}"
confirmed=0
clone_created=0

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/rehearse_notification_delivery_migrations_v311.sh \
    --confirm \
    [--source-db DATABASE] \
    [--clone-name test_DATABASE]

The command:
  - requires an explicit --confirm flag;
  - creates only a test_-prefixed disposable PostgreSQL clone;
  - never terminates database sessions;
  - applies migrations only to the disposable clone;
  - verifies post-apply schema and backfill evidence;
  - verifies the source database remains unchanged;
  - safely drops the disposable clone when it has no active connections.
USAGE
}

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
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
    --clone-name)
      [ "$#" -ge 2 ] || usage_error \
        "--clone-name requires a value"
      clone_name="$2"
      shift 2
      ;;
    --clone-name=*)
      clone_name="${1#*=}"
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

if [[ ! "$clone_name" =~ ^test_[a-z0-9_]+$ ]]; then
  usage_error \
    "clone name must match test_[a-z0-9_]+"
fi

if [ "$source_db" = "$clone_name" ]; then
  usage_error \
    "source and clone database names must differ"
fi

if [ ! -f docker-compose.yml ]; then
  usage_error \
    "run the rehearsal from the repository root"
fi

if [ ! -f backend/manage.py ]; then
  usage_error \
    "backend/manage.py is missing"
fi

validate_pre_apply_json() {
  PREFLIGHT_JSON="$1" \
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

if result.get("applied_target_count") != 0:
    errors.append(
        "target migrations are already applied"
    )

if result.get("pending_target_count") != 3:
    errors.append(
        "expected exactly three pending target migrations"
    )

if result.get("blocking_not_ready_count") != 0:
    errors.append(
        "blocking rollout checks remain"
    )

if result.get("read_only") is not True:
    errors.append(
        "preflight is not read-only"
    )

if result.get("mutation_allowed") is not False:
    errors.append(
        "preflight unexpectedly allows mutation"
    )

if errors:
    print("ERROR: pre-apply contract failed.")

    for error in errors:
        print("-", error)

    sys.exit(1)

print("status=ready_to_apply")
print("migration_mode=pre_apply")
print("pending_target_count=3")
PY
}

validate_post_apply_json() {
  PREFLIGHT_JSON="$1" \
  python - <<'PY'
import json
import os
import sys

result = json.loads(
    os.environ["PREFLIGHT_JSON"]
)

errors = []

if result.get("status") != "already_applied":
    errors.append(
        f"unexpected status: {result.get('status')!r}"
    )

if result.get("migration_mode") != "post_apply":
    errors.append(
        "database is not in post_apply mode"
    )

if result.get("applied_target_count") != 3:
    errors.append(
        "expected exactly three applied target migrations"
    )

if result.get("pending_target_count") != 0:
    errors.append(
        "target migrations remain pending"
    )

if result.get("pending_plan") != []:
    errors.append(
        "post-apply migration plan is not empty"
    )

if result.get("blocking_not_ready_count") != 0:
    errors.append(
        "blocking post-apply checks remain"
    )

if result.get("read_only") is not True:
    errors.append(
        "post-apply preflight is not read-only"
    )

if result.get("mutation_allowed") is not False:
    errors.append(
        "post-apply preflight unexpectedly allows mutation"
    )

if errors:
    print("ERROR: post-apply contract failed.")

    for error in errors:
        print("-", error)

    sys.exit(1)

print("status=already_applied")
print("migration_mode=post_apply")
print("applied_target_count=3")
PY
}

cleanup_clone() {
  original_status=$?
  cleanup_status=0

  trap - EXIT

  printf '\n===== DISPOSABLE DATABASE CLEANUP =====\n'

  clone_exists="$(
    docker compose exec -T \
      -e CLONE_NAME="$clone_name" \
      db sh -lc '
        psql \
          --set=ON_ERROR_STOP=1 \
          --username "$POSTGRES_USER" \
          --dbname postgres \
          --tuples-only \
          --no-align \
          --command "
            SELECT COUNT(*)
            FROM pg_database
            WHERE datname = '\''${CLONE_NAME}'\'';
          "
      ' 2>/dev/null
  )"

  exists_status=$?

  if [ "$exists_status" -ne 0 ]; then
    echo "ERROR: clone existence inspection failed."
    cleanup_status=1
  elif [ "$clone_exists" = "0" ]; then
    echo "Disposable rehearsal database is absent."
  else
    clone_connections="$(
      docker compose exec -T \
        -e CLONE_NAME="$clone_name" \
        db sh -lc '
          psql \
            --set=ON_ERROR_STOP=1 \
            --username "$POSTGRES_USER" \
            --dbname postgres \
            --tuples-only \
            --no-align \
            --command "
              SELECT COUNT(*)
              FROM pg_stat_activity
              WHERE datname = '\''${CLONE_NAME}'\'';
            "
        ' 2>/dev/null
    )"

    connections_status=$?

    if [ "$connections_status" -ne 0 ]; then
      echo "ERROR: clone connection inspection failed."
      cleanup_status=1
    elif [ "$clone_connections" != "0" ]; then
      echo "ERROR: disposable clone has active connections."
      echo "No session was terminated."
      echo "No forced database drop was attempted."
      cleanup_status=1
    else
      docker compose exec -T \
        -e CLONE_NAME="$clone_name" \
        db sh -lc '
          dropdb \
            --username "$POSTGRES_USER" \
            --maintenance-db postgres \
            "$CLONE_NAME"
        '

      drop_status=$?

      if [ "$drop_status" -ne 0 ]; then
        echo "ERROR: disposable clone drop failed."
        cleanup_status=1
      else
        echo "Disposable rehearsal database dropped safely."
      fi
    fi
  fi

  if [ "$original_status" -ne 0 ]; then
    exit "$original_status"
  fi

  exit "$cleanup_status"
}

trap cleanup_clone EXIT

printf '\n===== V311 DISPOSABLE MIGRATION REHEARSAL =====\n'
printf 'source_database=%s\n' "$source_db"
printf 'clone_database=%s\n' "$clone_name"

printf '\n===== VERIFY DISPOSABLE CLONE IS ABSENT =====\n'

existing_clone_count="$(
  docker compose exec -T \
    -e CLONE_NAME="$clone_name" \
    db sh -lc '
      psql \
        --set=ON_ERROR_STOP=1 \
        --username "$POSTGRES_USER" \
        --dbname postgres \
        --tuples-only \
        --no-align \
        --command "
          SELECT COUNT(*)
          FROM pg_database
          WHERE datname = '\''${CLONE_NAME}'\'';
        "
    '
)"

if [ "$existing_clone_count" != "0" ]; then
  fail \
    "disposable clone already exists; refusing to reuse it"
fi

echo "Disposable clone name is available."

printf '\n===== SOURCE PRE-APPLY PREFLIGHT =====\n'

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
validate_pre_apply_json "$source_preflight"

source_oid="$(
  docker compose exec -T \
    -e SOURCE_DB="$source_db" \
    db sh -lc '
      psql \
        --set=ON_ERROR_STOP=1 \
        --username "$POSTGRES_USER" \
        --dbname postgres \
        --tuples-only \
        --no-align \
        --command "
          SELECT oid
          FROM pg_database
          WHERE datname = '\''${SOURCE_DB}'\'';
        "
    '
)"

if [ -z "$source_oid" ]; then
  fail \
    "source database OID could not be recorded"
fi

printf 'source_database_oid=%s\n' "$source_oid"

printf '\n===== FAIL-CLOSED SOURCE CONNECTION CHECK =====\n'

source_connections="$(
  docker compose exec -T \
    -e SOURCE_DB="$source_db" \
    db sh -lc '
      psql \
        --set=ON_ERROR_STOP=1 \
        --username "$POSTGRES_USER" \
        --dbname postgres \
        --tuples-only \
        --no-align \
        --command "
          SELECT COUNT(*)
          FROM pg_stat_activity
          WHERE datname = '\''${SOURCE_DB}'\'';
        "
    '
)"

printf 'source_active_connections=%s\n' \
  "$source_connections"

if [ "$source_connections" != "0" ]; then
  fail \
    "source database has active connections; no clone was created"
fi

printf '\n===== CREATE DISPOSABLE TEMPLATE CLONE =====\n'

docker compose exec -T \
  -e SOURCE_DB="$source_db" \
  -e CLONE_NAME="$clone_name" \
  db sh -lc '
    createdb \
      --username "$POSTGRES_USER" \
      --maintenance-db postgres \
      --template "$SOURCE_DB" \
      "$CLONE_NAME"
  '

clone_created=1

echo "Disposable template clone created."

printf '\n===== CLONE IDENTITY CONTRACT =====\n'

clone_identity="$(
  docker compose exec -T \
    -e SOURCE_DB="$source_db" \
    -e CLONE_NAME="$clone_name" \
    db sh -lc '
      psql \
        --set=ON_ERROR_STOP=1 \
        --username "$POSTGRES_USER" \
        --dbname postgres \
        --tuples-only \
        --no-align \
        --command "
          SELECT
            source.oid::text
            || '\''|'\'' ||
            clone.oid::text
            || '\''|'\'' ||
            pg_database_size(clone.datname)::text
          FROM pg_database AS source
          JOIN pg_database AS clone
            ON clone.datname = '\''${CLONE_NAME}'\''
          WHERE source.datname = '\''${SOURCE_DB}'\'';
        "
    '
)"

IFS='|' read -r observed_source_oid clone_oid clone_size \
  <<< "$clone_identity"

printf 'observed_source_oid=%s\n' \
  "$observed_source_oid"
printf 'clone_database_oid=%s\n' \
  "$clone_oid"
printf 'clone_size_bytes=%s\n' \
  "$clone_size"

if [ "$observed_source_oid" != "$source_oid" ]; then
  fail \
    "source database OID changed during clone creation"
fi

if [ -z "$clone_oid" ] || [ "$clone_oid" = "$source_oid" ]; then
  fail \
    "disposable clone does not have a distinct OID"
fi

printf '\n===== CLONE PRE-APPLY PREFLIGHT =====\n'

clone_preflight="$(
  docker compose exec -T \
    -e DB_NAME="$clone_name" \
    -e PYTHONDONTWRITEBYTECODE=1 \
    web \
    python manage.py \
    check_notification_delivery_migration_rollout \
    --json
)"

printf '%s\n' "$clone_preflight"
validate_pre_apply_json "$clone_preflight"

printf '\n===== CLONE MIGRATION PLAN =====\n'

docker compose exec -T \
  -e DB_NAME="$clone_name" \
  -e PYTHONDONTWRITEBYTECODE=1 \
  web \
  python manage.py migrate \
  --plan \
  --noinput

printf '\n===== APPLY MIGRATIONS TO DISPOSABLE CLONE ONLY =====\n'

docker compose exec -T \
  -e DB_NAME="$clone_name" \
  -e PYTHONDONTWRITEBYTECODE=1 \
  web \
  python manage.py migrate \
  --noinput

printf '\n===== CLONE POST-APPLY PREFLIGHT =====\n'

clone_postflight="$(
  docker compose exec -T \
    -e DB_NAME="$clone_name" \
    -e PYTHONDONTWRITEBYTECODE=1 \
    web \
    python manage.py \
    check_notification_delivery_migration_rollout \
    --json
)"

printf '%s\n' "$clone_postflight"
validate_post_apply_json "$clone_postflight"

printf '\n===== CLONE GENERAL MIGRATION CHECK =====\n'

docker compose exec -T \
  -e DB_NAME="$clone_name" \
  -e PYTHONDONTWRITEBYTECODE=1 \
  web \
  python manage.py migrate \
  --check \
  --noinput

printf '\n===== CLONE SCHEMA AND BACKFILL EVIDENCE =====\n'

clone_evidence="$(
  docker compose exec -T \
    -e CLONE_NAME="$clone_name" \
    db sh -lc '
      psql \
        --set=ON_ERROR_STOP=1 \
        --username "$POSTGRES_USER" \
        --dbname "$CLONE_NAME" \
        --tuples-only \
        --no-align \
        --command "
          SELECT json_build_object(
            '\''auth_user_count'\'',
            (
              SELECT COUNT(*)
              FROM auth_user
            ),
            '\''verification_state_count'\'',
            (
              SELECT COUNT(*)
              FROM accounts_emailverificationstate
            ),
            '\''provider_receipt_count'\'',
            (
              SELECT COUNT(*)
              FROM listings_notificationprovideroutcomereceipt
            ),
            '\''retention_evidence_count'\'',
            (
              SELECT COUNT(*)
              FROM listings_notificationdeliveryretentionevidence
            ),
            '\''delivery_event_count'\'',
            (
              SELECT COUNT(*)
              FROM listings_notificationdeliveryevent
            ),
            '\''target_migration_count'\'',
            (
              SELECT COUNT(*)
              FROM django_migrations
              WHERE
                (
                  app = '\''accounts'\''
                  AND name =
                    '\''0016_emailverificationstate_v306'\''
                )
                OR
                (
                  app = '\''listings'\''
                  AND name IN (
                    '\''0024_notification_provider_outcomes_v307'\'',
                    '\''0025_notification_delivery_retention_v308'\''
                  )
                )
            ),
            '\''target_table_count'\'',
            (
              SELECT COUNT(*)
              FROM information_schema.tables
              WHERE
                table_schema = '\''public'\''
                AND table_name IN (
                  '\''accounts_emailverificationstate'\'',
                  '\''listings_notificationprovideroutcomereceipt'\'',
                  '\''listings_notificationdeliveryretentionevidence'\''
                )
            ),
            '\''target_column_count'\'',
            (
              SELECT COUNT(*)
              FROM information_schema.columns
              WHERE
                table_schema = '\''public'\''
                AND table_name =
                  '\''listings_notificationdeliveryevent'\''
                AND column_name IN (
                  '\''provider_event_id'\'',
                  '\''provider_message_id'\'',
                  '\''provider_name'\'',
                  '\''provider_outcome'\'',
                  '\''provider_outcome_at'\'',
                  '\''legal_hold'\'',
                  '\''legal_hold_reason'\'',
                  '\''legal_hold_set_at'\'',
                  '\''legal_hold_set_by_id'\'',
                  '\''retention_tombstoned_at'\'',
                  '\''retention_evidence_id'\''
                )
            ),
            '\''target_index_count'\'',
            (
              SELECT COUNT(*)
              FROM pg_class AS class
              JOIN pg_namespace AS namespace
                ON namespace.oid = class.relnamespace
              WHERE
                namespace.nspname = '\''public'\''
                AND class.relname IN (
                  '\''notif_provider_msg_idx'\'',
                  '\''notif_receipt_msg_idx'\'',
                  '\''notif_receipt_out_idx'\'',
                  '\''notif_retention_scan_idx'\''
                )
            ),
            '\''target_constraint_count'\'',
            (
              SELECT COUNT(*)
              FROM pg_constraint
              WHERE conname IN (
                '\''notif_provider_event_uniq'\'',
                '\''notif_legal_hold_metadata'\'',
                '\''notif_retention_evidence_req'\''
              )
            )
          )::text;
        "
    '
)"

printf '%s\n' "$clone_evidence"

EVIDENCE_JSON="$clone_evidence" \
python - <<'PY'
import json
import os
import sys

result = json.loads(
    os.environ["EVIDENCE_JSON"]
)

errors = []

if (
    result["verification_state_count"]
    != result["auth_user_count"]
):
    errors.append(
        "verification-state backfill does not cover every user"
    )

expected_counts = {
    "target_migration_count": 3,
    "target_table_count": 3,
    "target_column_count": 11,
    "target_index_count": 4,
    "target_constraint_count": 3,
    "provider_receipt_count": 0,
    "retention_evidence_count": 0,
    "delivery_event_count": 0,
}

for key, expected in expected_counts.items():
    if result.get(key) != expected:
        errors.append(
            f"{key}={result.get(key)!r}; expected {expected}"
        )

if errors:
    print("ERROR: clone evidence contract failed.")

    for error in errors:
        print("-", error)

    sys.exit(1)

print("verification_backfill=complete")
print("target_tables=3")
print("target_columns=11")
print("target_indexes=4")
print("target_constraints=3")
print("delivery_data=unchanged")
PY

printf '\n===== SOURCE POST-REHEARSAL PREFLIGHT =====\n'

source_postflight="$(
  docker compose exec -T \
    -e DB_NAME="$source_db" \
    -e PYTHONDONTWRITEBYTECODE=1 \
    web \
    python manage.py \
    check_notification_delivery_migration_rollout \
    --json
)"

printf '%s\n' "$source_postflight"
validate_pre_apply_json "$source_postflight"

observed_source_oid="$(
  docker compose exec -T \
    -e SOURCE_DB="$source_db" \
    db sh -lc '
      psql \
        --set=ON_ERROR_STOP=1 \
        --username "$POSTGRES_USER" \
        --dbname postgres \
        --tuples-only \
        --no-align \
        --command "
          SELECT oid
          FROM pg_database
          WHERE datname = '\''${SOURCE_DB}'\'';
        "
    '
)"

if [ "$observed_source_oid" != "$source_oid" ]; then
  fail \
    "source database OID changed during rehearsal"
fi

echo "Source database OID remained unchanged."

printf '\n===== V311 REHEARSAL RESULT =====\n'
echo "Disposable notification migration rehearsal passed."
echo "Cleanup will now remove the disposable clone."
