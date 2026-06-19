#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ "${1:-}" = "" ]; then
    echo "Usage: bash scripts/restore_postgres.sh backups/postgres_YYYYMMDD_HHMMSS.sql.gz"
    exit 1
fi

BACKUP="$1"

if [ ! -f "${BACKUP}" ]; then
    echo "Backup file not found: ${BACKUP}"
    exit 1
fi

DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-postgres}"

echo "WARNING: This will restore into database '${DB_NAME}'."
echo "Press Enter to continue, or Ctrl+C to cancel."
read -r

echo "Restoring PostgreSQL backup: ${BACKUP}"

gunzip -c "${BACKUP}" | docker compose exec -T db psql -U "${DB_USER}" "${DB_NAME}"

echo "Restore complete."
