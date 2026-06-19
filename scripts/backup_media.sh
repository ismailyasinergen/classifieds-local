#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

mkdir -p backups

STAMP="$(date +"%Y%m%d_%H%M%S")"
OUT="backups/media_${STAMP}.tar.gz"

echo "Creating media backup: ${OUT}"

docker compose run --rm --entrypoint "" web tar -czf - -C /app media > "${OUT}"

echo "Done: ${OUT}"
