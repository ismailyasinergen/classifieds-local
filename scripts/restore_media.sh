#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ "${1:-}" = "" ]; then
    echo "Usage: bash scripts/restore_media.sh backups/media_YYYYMMDD_HHMMSS.tar.gz"
    exit 1
fi

BACKUP="$1"

if [ ! -f "${BACKUP}" ]; then
    echo "Backup file not found: ${BACKUP}"
    exit 1
fi

echo "WARNING: This will restore media files into the web container media folder."
echo "Press Enter to continue, or Ctrl+C to cancel."
read -r

echo "Restoring media backup: ${BACKUP}"

cat "${BACKUP}" | docker compose run --rm --entrypoint "" web tar -xzf - -C /app

echo "Media restore complete."
