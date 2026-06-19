#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

mkdir -p backups

STAMP="$(date +"%Y%m%d_%H%M%S")"
OUT="backups/postgres_${STAMP}.sql.gz"

DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-postgres}"

echo "Creating PostgreSQL backup: ${OUT}"

docker compose exec -T db pg_dump -U "${DB_USER}" "${DB_NAME}" | gzip > "${OUT}"

echo "Done: ${OUT}"
