#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."

while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done

echo "PostgreSQL is ready."

auto_migrate="${DJANGO_AUTO_MIGRATE:-0}"

case "$auto_migrate" in
  1|true|TRUE|True|yes|YES|Yes|on|ON|On)
    echo "Applying database migrations..."
    python manage.py migrate --noinput
    ;;
  0|false|FALSE|False|no|NO|No|off|OFF|Off)
    echo "Checking for unapplied database migrations..."

    if ! python manage.py migrate --check --noinput; then
      echo >&2 "ERROR: unapplied database migrations detected."
      echo >&2 "Apply migrations with an operator-controlled one-off command before starting the application."
      exit 1
    fi

    echo "Database migration preflight passed."
    ;;
  *)
    echo >&2 "ERROR: DJANGO_AUTO_MIGRATE must be a boolean value."
    exit 2
    ;;
esac

echo "Archiving expired listings..."
python manage.py archive_expired_listings

echo "Expiring featured placements..."
python manage.py expire_featured_listings

echo "Expiring promotion packages..."
python manage.py expire_promotions

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting app..."
exec "$@"
