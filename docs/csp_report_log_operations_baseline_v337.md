# Sanitized CSP report log-operations baseline v337

## Outcome

V337 gives sanitized V334 CSP evidence a dedicated, fail-closed log route.
The `security.csp_report_v334` logger now uses:

- one dedicated `INFO` stream handler targeting stdout;
- a V337 structured JSON formatter;
- `propagate: false`, preventing duplicate delivery through the root logger;
- the existing independent ingestion gate, so disabled collection emits no
  evidence.

The formatter never renders the original log message, formatting arguments, or
exception. It accepts only the exact 11-field evidence schema produced by the
V334 sanitizer, with approved media types, report index, resources,
directives, disposition, and numeric bounds. A missing, reordered, malformed,
or forged evidence object produces only:

```json
{"event":"csp_report_log_rejected_v337","schema_version":1}
```

Valid events contain the fixed `csp_violation_v334` event name, schema version
one, and sanitized evidence. URL paths, queries, fragments, credentials,
policies, referrers, script samples, and the original message remain absent.

## Bounded production retention

The production Compose override configures the web container with Docker's
`local` log driver:

```text
max-size=10m
max-file=5
compress=true
```

This bounds and compresses the node-local Docker copy of all web stdout/stderr,
including the dedicated CSP stream. It does not write a CSP report model,
application file, or raw payload.

The resolved Compose JSON can be piped directly into the bounded, read-only
validator:

```text
DJANGO_ENV_FILE=.env.production.example docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production.example config --format json | python backend/scripts/check_csp_report_log_retention_v337.py --strict
```

The validator reads at most 1 MiB from stdin or an explicitly supplied file,
does not echo Compose content, and reports seven fixed checks for the web
service, local driver, size, file count, and compression. The direct pipe
avoids creating a resolved configuration file that could contain secrets.

## Operational boundary

Docker-daemon access grants access to the sanitized evidence. Host membership,
external collection, export, search, backup, and deletion policies still
require independent approval. The local rotation baseline does not
automatically satisfy or set the V335 log-governance attestation.

An external logging driver may replace this node-local baseline, but the
deployment must then supply equivalent bounded retention and access evidence.
The V337 validator intentionally fails if the committed production baseline is
silently widened or changed.

## Validation

- V334/V337 focused package: 30 tests passed in 0.269 seconds.
- V324-V337 asset/CSP chain plus production settings: 146 tests passed in
  74.811 seconds.
- Final PostgreSQL regression: 3,011 tests passed in 427.424 seconds; measured
  wall-clock time was 449.0 seconds.
- Resolved production Compose retention validator: seven of seven checks
  ready.
- Docker Engine accepted the `local` driver with the configured rotation and
  compression options.
- Production Compose configuration validation: passed.
- Synthetic formatter smoke: sanitized JSON emitted, response `204`, and no
  CSP enforcement header.
- V335 reviewed production-like strict audit: 13 of 13 checks ready.
- `manage.py check` and `manage.py check --tag templates`: zero issues.
- `makemigrations --check --dry-run`: no changes detected.
- `migrate --check --noinput`: passed without applying migrations.
- `collectstatic --dry-run --noinput`: passed.
- `git diff --check`: passed.
- No migration was created or applied; the development database was not
  mutated.

Checkpoint: `project-checkpoint-v337-csp-report-log-operations`.

The selected follow-up is v338, a safe CSP observation synthetic-delivery
smoke harness using invented payloads, explicit target controls, bounded
timeouts, sanitized evidence assertions, and no enforcement enablement.
