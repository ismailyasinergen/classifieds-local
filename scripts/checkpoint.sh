#!/usr/bin/env bash
set -euo pipefail

echo ""
echo "== Django system check =="
docker compose run --rm --entrypoint "" web python manage.py check

echo ""
echo "== Django test suite =="
docker compose run --rm --entrypoint "" web python manage.py test -v 2

echo ""
echo "== Rebuild and start containers =="
docker compose up -d --build

echo ""
echo "== Container status =="
sleep 10
docker compose ps

echo ""
echo "== Web logs =="
docker compose logs web --tail=80

echo ""
echo "== Git status =="
git status --short

echo ""
echo "Checkpoint complete."
