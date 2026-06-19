#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."

while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done

echo "PostgreSQL is ready."

echo "Running migrations..."
python manage.py migrate

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
