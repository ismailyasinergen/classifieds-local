# CSP report edge abuse-control baseline v336

## Outcome

V336 adds an exact-path Nginx boundary for the built-in V334 report receiver:

```text
location = /__csp_reports__/
```

The boundary has a 16 KiB body limit, a ten-second body timeout, and a shared
client-IP request zone averaging one request per second. Ten excess requests
may pass immediately as a short burst; further excess requests receive `429`.
Rate enforcement is active rather than dry-run, and limit events use Nginx's
`notice` log level.

The exact location preserves the existing upstream target, redirect behavior,
host, real-IP, forwarded-for, and forwarded-protocol headers. The fallback
application proxy remains unchanged. V336 adds no CSP enforcement header,
report persistence, Django setting, URL, model, or migration.

## Configuration validator

The bounded, read-only validator can be run before deployment:

```text
python backend/scripts/check_csp_report_edge_config_v336.py --strict
python backend/scripts/check_csp_report_edge_config_v336.py --json
docker compose exec -T nginx nginx -t
```

Its 13 fail-closed checks require:

- a readable configuration no larger than 256 KiB;
- the exact shared zone declaration keyed by binary remote address;
- one and only one exact report location;
- the endpoint body size and timeout;
- active rate limiting, `429`, and the approved log level;
- the expected upstream target and forwarding headers;
- the existing fallback application proxy;
- no `limit_req_dry_run on`;
- no Nginx `Content-Security-Policy` enforcement header.

Comments are removed before evaluation so a commented directive cannot satisfy
a check. Text and JSON output contain only fixed identifiers, reason codes,
counts, status, and the V336 marker. The validator does not reload Nginx,
contact the network, or write a file or database.

## Live local evidence

After native `nginx -t` validation and a local reload:

- a small report POST reached default-off Django ingestion and returned `404`;
- a 17,000-byte POST was rejected by Nginx with `413`;
- a fresh concurrent batch of 30 report POSTs produced 11 Django `404`
  responses and 19 Nginx `429` responses.

The first 11 accepted requests match one base request plus the configured
ten-request burst. The default-off application gate and the absence of
enforcement remain unchanged.

## Deployment boundary

The 10 MiB Nginx state zone is shared across workers on one proxy node. It is
not distributed across multiple Nginx nodes. Multi-node deployments still
need a deployment-wide upstream limit before the V335 edge attestation is
approved.

The zone uses Nginx's remote address. When another load balancer is placed
before Nginx, trusted real-client-IP restoration must be configured and
verified first; otherwise unrelated clients may share the load balancer's
limit key.

## Validation

- V336 focused package: 10 tests passed in 0.050 seconds.
- V324-V336 asset/CSP chain plus production settings: 135 tests passed in
  77.313 seconds.
- Final PostgreSQL regression: 3,000 tests passed in 427.727 seconds; measured
  wall-clock time was 449.5 seconds.
- Read-only Nginx validator: 13 of 13 checks ready.
- Native `nginx -t`: syntax valid and configuration test successful.
- Live proxy boundary: small `404`, oversized `413`, concurrent 11 `404` plus
  19 `429`.
- `manage.py check` and `manage.py check --tag templates`: zero issues.
- `makemigrations --check --dry-run`: no changes detected.
- `migrate --check --noinput`: passed without applying migrations.
- `collectstatic --dry-run --noinput`: passed.
- `git diff --check`: passed.
- No migration was created or applied; the development database was not
  mutated.

Checkpoint: `project-checkpoint-v336-csp-report-edge-abuse-control`.

The selected follow-up is v337, a sanitized CSP report log-operations baseline
covering dedicated routing, bounded local retention evidence, and continued
separation from report payload persistence and CSP enforcement.
