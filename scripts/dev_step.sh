#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

RUN_MIGRATIONS=0
SKIP_BUILD=0
PATCH_ONLY=0

for arg in "$@"; do
    case "$arg" in
        --migrate)
            RUN_MIGRATIONS=1
            ;;
        --skip-build)
            SKIP_BUILD=1
            ;;
        --patch-only)
            PATCH_ONLY=1
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Allowed options: --migrate --skip-build --patch-only"
            exit 1
            ;;
    esac
done

if [ ! -f "docker-compose.yml" ] && [ ! -f "docker-compose.yaml" ]; then
    echo "ERROR: Run this from the project root:"
    echo "/c/Users/ismai/Desktop/classifieds_local"
    exit 1
fi

echo "Project root:"
pwd
echo

echo "Stopping web container..."
docker compose stop web || true
echo

if [ ! -t 0 ]; then
    PATCH_FILE=".dev_step_patch_$(date +"%Y%m%d_%H%M%S").py"
    cat > "$PATCH_FILE"

    if [ -s "$PATCH_FILE" ]; then
        echo "Applying patch script: $PATCH_FILE"
        python "$PATCH_FILE"
    else
        echo "No patch content received."
    fi

    rm -f "$PATCH_FILE"
    echo
else
    echo "No patch script provided through stdin."
    echo
fi

if [ "$PATCH_ONLY" -eq 1 ]; then
    echo "Patch-only mode complete."
    exit 0
fi

if [ "$RUN_MIGRATIONS" -eq 1 ]; then
    echo "Running makemigrations..."
    docker compose run --rm --entrypoint "" web python manage.py makemigrations
    echo

    echo "Running migrate..."
    docker compose run --rm --entrypoint "" web python manage.py migrate
    echo
fi

echo "Running Django system check..."
docker compose run --rm --entrypoint "" web python manage.py check
echo

if [ "$SKIP_BUILD" -eq 1 ]; then
    echo "Starting web without rebuild..."
    docker compose start web
else
    echo "Rebuilding and starting services..."
    docker compose up -d --build
fi

echo
echo "Waiting for web startup..."
sleep 10

echo
echo "Container status:"
docker compose ps

echo
echo "Recent web logs:"
docker compose logs web --tail=80

echo
echo "Done."
