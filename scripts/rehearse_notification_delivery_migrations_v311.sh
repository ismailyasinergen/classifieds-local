#!/usr/bin/env bash

set -euo pipefail

repository_root="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
  pwd
)"

cd "$repository_root"

exec bash \
  "$repository_root/backend/scripts/rehearse_notification_delivery_migrations_v311.sh" \
  "$@"
