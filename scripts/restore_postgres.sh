#!/usr/bin/env bash

set -euo pipefail

repository_root="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
  pwd
)"

cd "$repository_root"

exec bash \
  "$repository_root/backend/scripts/restore_verified_postgres_backup_v314.sh" \
  "$@"
