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

V337 routes `security.csp_report_v334` through a dedicated non-propagating
stdout handler. Its formatter ignores the original log message and renders
only the exact validated evidence schema as compact JSON. Missing, malformed,
or forged evidence produces a fixed `csp_report_log_rejected_v337` event
without echoing the rejected value, exception, or format arguments.

The production Compose override uses Docker's `local` log driver for the web
container with 10 MiB rotation size, five files, and compression. This bounds
the node-local copy of all web-container stdout/stderr, including the dedicated
CSP stream. Validate the resolved configuration without creating a secret-
bearing temporary file:

DJANGO_ENV_FILE=.env.production.example docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production.example config --format json | python backend/scripts/check_csp_report_log_retention_v337.py --strict

The validator reads bounded Compose JSON from stdin and emits only fixed status
and reason codes. In a real deployment, substitute the approved environment
file while keeping the pipe direct. Access to Docker logs grants access to the
sanitized evidence, so Docker-daemon membership and any external collector
must have approved access, export, and deletion controls. The local rotation
baseline alone does not justify setting
`DJANGO_CSP_OBSERVATION_LOG_GOVERNANCE_APPROVED=1`.

V338 packages a privacy-safe synthetic delivery harness. Its default mode only
plans and performs no network request:

python backend/scripts/run_csp_observation_smoke_v338.py --target-url https://your-domain.com/__csp_reports__/ --confirm-remote-host your-domain.com

Copy the generated `smoke_id`, review the target, then send exactly one
invented report:

python backend/scripts/run_csp_observation_smoke_v338.py --target-url https://your-domain.com/__csp_reports__/ --confirm-remote-host your-domain.com --smoke-id <16-lowercase-hex> --execute

Successful delivery requires `204`, `Cache-Control: no-store`, an empty body,
and no `Content-Security-Policy` enforcement header. Remote targets require
HTTPS and an exact hostname confirmation. Loopback HTTP is allowed for local
testing. Credentials, redirects, proxies, cookies, query strings, fragments,
other paths, and timeouts above ten seconds are rejected or disabled.

Verify the same smoke identifier against one exact V337 JSON line. Docker
Compose prefixes must be disabled:

docker compose logs --since 5m --no-color --no-log-prefix web | python backend/scripts/run_csp_observation_smoke_v338.py --target-url https://your-domain.com/__csp_reports__/ --confirm-remote-host your-domain.com --smoke-id <16-lowercase-hex> --verify-log-stdin

The log input is limited to 512 KiB and is never echoed. For an external
collector, pipe an equivalent bounded export containing the standalone JSON
line. The harness uses only `.invalid` synthetic origins and never changes CSP
gates, enforcement, or the V335 attestations. Set
`DJANGO_CSP_OBSERVATION_SYNTHETIC_REPORT_VERIFIED=1` only after both delivery
and log verification pass in the reviewed deployment.

V339 closes the V333-V338 evidence chain without contacting the deployment or
changing it. Keep the five sanitized JSON outputs in an operator-controlled
directory outside the repository:

1. V335 `--json --strict` readiness output from the final reviewed
   configuration.
2. V336 `--json --strict` edge-validator output.
3. V337 `--json --strict` resolved-Compose retention output.
4. V338 `--execute --json` delivery output.
5. V338 `--verify-log-stdin --json` log-verification output using the same
   smoke identifier, origin, timeout, and expected-log digest.

Generate the V335 evidence only after the external edge and log-governance
reviews are approved, the V338 delivery and log checks pass, the corresponding
attestations are set, and the reviewed application configuration is active.
Then run:

python backend/scripts/check_csp_observation_evidence_closeout_v339.py --readiness-json <v335.json> --edge-json <v336.json> --retention-json <v337.json> --delivery-json <v338-delivery.json> --log-json <v338-log.json> --expected-origin https://your-domain.com --strict

Each input is limited to 128 KiB. The closeout requires exact component
schemas, all component checks ready, a safe exact expected origin, linked V338
smoke evidence, and independent absence of application, edge, and response
enforcement. Its output contains only fixed identifiers, counts, and reason
codes; it never repeats the hostname, smoke ID, digest, file content, or file
path.

V339 validates structural consistency, not evidence authenticity, freshness,
deployment identity, collector governance, or multi-node edge behavior.
Operators must collect all five artifacts from the same reviewed deployment
and change window. The audit performs no network, Docker, file-write, database,
environment, CSP gate, enforcement, or attestation mutation.

V340 analyzes one explicitly bounded UTC observation window after V339
closeout has passed. It reads an approved V339 closeout JSON file and
newline-delimited sanitized V337 observation records from standard input:

python backend/scripts/analyze_csp_observation_window_v340.py --closeout-json <v339-closeout.json> --window-start 2026-07-20T00:00:00Z --window-end 2026-07-21T00:00:00Z --json --strict < <sanitized-v337-window.jsonl>

Each non-empty JSONL line must contain exactly `observed_at`, `event`,
`schema_version`, and the exact sanitized V337 `evidence` object. The
wrapper must come from an approved bounded export. Do not pipe raw browser
reports, Docker prefixes, request bodies, script samples, URL paths,
queries, fragments, cookies, credentials, or arbitrary logs into V340.

The analyzer accepts at most 1 MiB and 10,000 records. The UTC window must
be at least 60 seconds and no longer than exactly seven days; its start is
inclusive and its end is exclusive. Each deterministic summary is capped
at eight buckets, with overflow combined under `__other__`. HTTP and HTTPS
blocked resources are reduced to the fixed class `origin`.

Synthetic V338 `.invalid` observations are counted separately from organic
observations. Empty and synthetic-only windows remain analyzable but carry
explicit reason codes requiring operator review.

V340 emits bounded counts and summaries only. It performs no network,
Docker, subprocess, file-write, database, environment, CSP gate,
enforcement, or automatic-decision operation.


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
