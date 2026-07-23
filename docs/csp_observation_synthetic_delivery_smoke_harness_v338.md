# CSP observation synthetic-delivery smoke harness v338

## Outcome

V338 packages a privacy-safe, operator-invoked harness for proving that one
invented CSP report can traverse the reviewed observation path. It has three
explicit modes:

- plan: build and display only sanitized metadata, without network access;
- execute: send exactly one `application/csp-report` POST;
- verify: accept bounded log input on stdin and require exactly one matching
  standalone V337 JSON evidence line.

The harness never changes Django settings, CSP gates, enforcement headers,
V335 attestations, files, or database state.

## Target and payload controls

The target must use the exact `/__csp_reports__/` path without credentials,
query strings, or fragments. Plain HTTP is accepted only for literal loopback
hosts. Every remote target requires HTTPS plus
`--confirm-remote-host <hostname>`, with an exact normalized hostname match.

The report uses a 16-character lowercase hexadecimal smoke identifier and
only reserved `.invalid` origins. Its deliberately invented paths, token-like
values, and script sample exercise the V334 sanitizer; they never appear in
the expected or observed V337 evidence. The plan exposes the SHA-256 digest of
the exact expected log line so an operator can compare evidence without
printing the raw report.

## Delivery contract

Execution uses a timeout bounded from one to ten seconds, disables environment
proxies and redirects, stores no cookies, reads at most 1,024 response bytes,
and makes one request. Success requires all of the following:

- HTTP `204`;
- `Cache-Control` containing `no-store`;
- an empty response body;
- no `Content-Security-Policy` enforcement header.

Network and HTTP failures are reduced to fixed reason codes and sanitized
status metadata. The harness does not print response content or rejected
configuration values.

## Log verification

After a successful delivery, pipe a bounded export from the reviewed log
destination into `--verify-log-stdin`. Docker Compose log prefixes must be
disabled so the formatter's compact JSON is a standalone line. Input is
limited to 512 KiB, never echoed, and passes only when exactly one line equals
the expected V337 event. Prefixed, duplicated, malformed, missing, and
oversized evidence fails closed.

This proves synthetic delivery only for the reviewed deployment and capture
window. An operator may set
`DJANGO_CSP_OBSERVATION_SYNTHETIC_REPORT_VERIFIED=1` only after both execution
and log verification pass there. The harness does not set that attestation.

## Validation

- V338 focused package: 14 tests passed in 0.588 seconds.
- V324-V338 asset/CSP chain plus production settings: 160 tests passed in
  80.586 seconds.
- Final PostgreSQL regression: 3,025 tests passed in 427.135 seconds; measured
  wall-clock time was 449.3 seconds.
- Plan-mode CLI: deterministic sanitized evidence and no network access.
- Remote HTTP rejection: failed before network access with no target echo.
- Exact log-verification CLI: one matching V337 line accepted.
- Live Django loopback delivery: response `204`, `no-store`, empty body, no
  enforcement header, and only sanitized V337 evidence captured.
- Redirect, proxy, cookie, timeout, body-read, and log-input bounds: covered.
- `manage.py check` and `manage.py check --tag templates`: zero issues.
- `makemigrations --check --dry-run`: no changes detected.
- `migrate --check --noinput`: passed without applying migrations.
- `collectstatic --dry-run --noinput`: passed.
- `git diff --check`: passed.
- No migration was created or applied; the development database was not
  mutated.

Checkpoint:
`project-checkpoint-v338-csp-observation-synthetic-delivery-smoke`.

The selected follow-up is v339, a read-only CSP observation evidence closeout
audit that ties the V333-V338 controls together without enabling enforcement
or changing production attestations.
