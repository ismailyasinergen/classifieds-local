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
DJANGO_CSP_REPORT_ONLY_REPORT_URI=/__csp_reports__/
DJANGO_CSP_REPORT_INGESTION_ENABLED=1

The report URI may be a same-origin absolute path or a credential-free HTTPS
collector URI. Leave it empty to use browser developer-console observation
without server-side collection. Review violations and update source contracts
before considering enforcement.

The built-in `/__csp_reports__/` endpoint is independently default-off. It
accepts only CSP report media types, limits request and batch sizes, applies a
hashed-client in-process cache rate limit, and emits sanitized structured logs
without database persistence. Production still requires proxy-level
distributed rate limiting and approved log retention/access controls.

V335 packages a read-only readiness command. It does not send a report,
contact the network, change configuration, write application data, or enable
enforcement:

python manage.py check_csp_observation_readiness_v335
python manage.py check_csp_observation_readiness_v335 --json
python manage.py check_csp_observation_readiness_v335 --strict

The strict result remains `not_ready` until both application gates target the
built-in path and all three external prerequisites have been independently
reviewed:

DJANGO_CSP_OBSERVATION_EDGE_RATE_LIMIT_APPROVED=1
DJANGO_CSP_OBSERVATION_LOG_GOVERNANCE_APPROVED=1
DJANGO_CSP_OBSERVATION_SYNTHETIC_REPORT_VERIFIED=1

These values are attestations, not substitutes for the controls. Before
setting them, verify that the edge has a distributed limit specifically for
`/__csp_reports__/`; that sanitized `security.csp_report_v334` INFO events have
approved retention, access and export controls; and that a same-origin
synthetic `application/csp-report` POST returns 204 and reaches that sanitized
log destination. Confirm that the response still has no
`Content-Security-Policy` enforcement header. Never include a real URL,
account, token or script sample in the synthetic payload.

V336 adds a single-node Nginx edge baseline for the built-in path:

- a 10 MiB shared client-IP state zone averaging one request per second;
- a ten-request immediate burst allowance with active enforcement;
- a `429` response for excess requests;
- a 16 KiB endpoint body limit and ten-second body timeout;
- unchanged upstream target and forwarding headers;
- no CSP enforcement header or report persistence.

Validate the committed configuration before deployment:

python backend/scripts/check_csp_report_edge_config_v336.py --strict
python backend/scripts/check_csp_report_edge_config_v336.py --json
docker compose exec -T nginx nginx -t

The Nginx zone is shared across workers on one node, not across multiple proxy
nodes. A multi-node deployment still needs a deployment-wide upstream limit.
If another load balancer is placed before Nginx, configure and verify trusted
real-client-IP restoration before approving the edge check; otherwise clients
may be grouped under the load balancer address.


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
