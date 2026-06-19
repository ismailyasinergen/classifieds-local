#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "========================================"
echo "Classifieds Local Production Preflight"
echo "========================================"
echo

echo "1) Checking Docker Compose files..."
docker compose config > /tmp/classifieds_local_compose_dev.yml

if [ -f docker-compose.prod.yml ]; then
    if [ -f .env.production ]; then
        docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production config > /tmp/classifieds_local_compose_prod.yml
        echo "Production compose config: OK"
    else
        docker compose -f docker-compose.yml -f docker-compose.prod.yml config > /tmp/classifieds_local_compose_prod.yml
        echo "Production compose config: OK"
        echo "Note: .env.production not found, so only compose structure was checked."
    fi
else
    echo "WARNING: docker-compose.prod.yml not found."
fi

echo
echo "2) Starting database if needed..."
docker compose up -d db
sleep 5

echo
echo "3) Running normal Django check..."
docker compose run --rm --entrypoint "" web python manage.py check

echo
echo "4) Running production-style Django deploy check..."
if [ -f .env.production ]; then
    docker compose --env-file .env.production run --rm --entrypoint "" web python manage.py check --deploy
else
    docker compose run --rm --entrypoint "" \
      -e DJANGO_DEBUG=0 \
      -e DJANGO_SECRET_KEY=production-check-secret-key-change-me-production-check-secret-key \
      -e DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 \
      -e DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1 \
      -e DJANGO_SECURE_SSL_REDIRECT=1 \
      -e DJANGO_SESSION_COOKIE_SECURE=1 \
      -e DJANGO_CSRF_COOKIE_SECURE=1 \
      -e DJANGO_SECURE_HSTS_SECONDS=31536000 \
      -e DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=1 \
      web python manage.py check --deploy
fi

echo
echo "5) Rebuilding and starting local development stack..."
docker compose up -d --build
sleep 10

echo
echo "6) Container status:"
docker compose ps

echo
echo "7) Health endpoint check from host:"
if command -v curl >/dev/null 2>&1; then
    curl -fsS http://localhost/healthz/
    echo
else
    echo "curl not found. Open http://localhost/healthz/ manually."
fi

echo
echo "8) Recent web logs:"
docker compose logs web --tail=80

echo
echo "========================================"
echo "Preflight complete."
echo "========================================"
