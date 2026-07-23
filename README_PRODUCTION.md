# Production Settings

Copy .env.production.example to your real production environment and set real values.

Required production values:

DJANGO_DEBUG=0
DJANGO_SECRET_KEY=<long random secret>
DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com
DJANGO_SECURE_SSL_REDIRECT=1
DJANGO_SESSION_COOKIE_SECURE=1
DJANGO_CSRF_COOKIE_SECURE=1
DJANGO_SECURE_HSTS_SECONDS=31536000

Local development can continue with the normal Docker Compose setup.


CSP Report-Only Observation
===========================

V333 adds an environment-controlled observation policy. It is disabled by
default and does not emit a `Content-Security-Policy` enforcement header.

Enable it only after selecting where browser reports will be reviewed:

DJANGO_CSP_REPORT_ONLY_ENABLED=1
DJANGO_CSP_REPORT_ONLY_REPORT_URI=/approved-csp-report-path/

The report URI may be a same-origin absolute path or a credential-free HTTPS
collector URI. Leave it empty to use browser developer-console observation
without server-side collection. Review violations and update source contracts
before considering enforcement.


Production Docker Compose
=========================

Local development:

docker compose up -d --build

Production-style run:

cp .env.production.example .env.production

Then edit .env.production and set real values.

Start production-style containers:

docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d --build

Run production checks:

docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production run --rm --entrypoint "" web python manage.py check --deploy

Stop production-style containers:

docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production down

Notes:
- prod_static stores collected static files.
- prod_media stores uploaded media files.
- The app still needs real domain, HTTPS, and backup setup before live deployment.


Custom Error Pages
==================

Production uses custom templates for:

404 Page not found
403 Permission denied
500 Server error
405 Method not allowed

In local development with DJANGO_DEBUG enabled, Django may still show debug error pages.
To test production-style errors, run checks or start with DJANGO_DEBUG=0.


Health Check
============

The app exposes:

/healthz/

Expected healthy response:

status: ok
checks.app: ok
checks.database: ok

Use this URL from uptime monitors, load balancers, or Docker healthchecks.

Production Preflight
====================

Run this before production-style deployment or after major changes:

bash scripts/prod_preflight.sh

The script checks:
- Docker Compose config
- Django system check
- Django production deploy check
- local stack rebuild
- /healthz/ endpoint
- recent web logs

If .env.production exists, the script uses it for the production deploy check.
If .env.production does not exist, it uses safe temporary test values.\n\n
Appeal Evidence Deadline Reminders
==================================

Run this command periodically in production, for example every 24 hours:

docker compose exec web python manage.py send_appeal_evidence_deadline_reminders

It sends:
- reminder notices when an appeal extra-evidence deadline is within 15 days
- overdue notices when the deadline passes
- no duplicate reminder/overdue notices

Final appeal decisions are still manual.
