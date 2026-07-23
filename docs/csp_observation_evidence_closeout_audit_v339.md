# CSP observation evidence closeout audit v339

## Outcome

V339 closes the V333-V338 CSP observation evidence chain with a standalone,
read-only aggregator:

```text
python backend/scripts/check_csp_observation_evidence_closeout_v339.py \
  --readiness-json <v335.json> \
  --edge-json <v336.json> \
  --retention-json <v337.json> \
  --delivery-json <v338-delivery.json> \
  --log-json <v338-log.json> \
  --expected-origin https://your-domain.com \
  --strict
```

It accepts only the sanitized JSON emitted by the existing V335 readiness,
V336 edge, V337 retention, and separate V338 execute and log-verification
paths. Each file is read at most once and is limited to 128 KiB.

The aggregator performs no network request, Docker command, subprocess,
environment change, file write, database access, report delivery, CSP gate
change, enforcement enablement, or attestation mutation.

## Closeout contract

Eight fail-closed checks require:

- a credential-free exact HTTPS origin, with plain HTTP allowed only for a
  literal loopback origin;
- an exact, fully ready V335 result with all 13 ordered checks;
- an exact, fully ready V336 result with all 13 ordered checks;
- an exact, fully ready V337 result with all seven ordered checks;
- a passing V338 execute result with `204`, `no-store`, an empty-body
  contract, and no enforcement header;
- a passing, separate V338 log-verification result;
- identical smoke identifier, target origin, target path, timeout, and
  expected-log digest across the two V338 artifacts;
- independently ready application, edge, and delivery evidence for absence of
  CSP enforcement.

Extra fields, reordered component checks, forged counts, non-boolean state,
unknown success claims, unsafe origins, malformed or oversized files, and
unlinked smoke artifacts fail closed.

## Privacy and evidence boundary

Text and JSON output contain only the V339 marker, eight fixed check
identifiers, fixed reason codes, status values, and counts. The output never
repeats:

- the expected or observed hostname;
- the smoke identifier;
- the expected-log digest;
- an input path;
- input file content;
- raw CSP report material.

V339 validates structure and cross-artifact consistency. It does not
cryptographically authenticate a file, establish when it was generated,
identify the deployment that generated it, inspect an external collector, or
prove a multi-node edge policy. Operators remain responsible for collecting
all five artifacts from the same reviewed deployment and change window and
protecting them under the approved evidence-retention policy.

## Scope

Changed files:

- `backend/scripts/check_csp_observation_evidence_closeout_v339.py`
- `backend/config/tests/test_csp_observation_evidence_closeout_audit_v339.py`
- `docs/csp_observation_evidence_closeout_audit_v339.md`
- `README_PRODUCTION.md`
- `ROADMAP_STATUS.md`

No model, migration, route, view, middleware, setting, template, static asset,
Nginx rule, Compose service, or production environment default changed.

## Validation

- V339 focused audit: 14 tests passed in 0.109 seconds.
- V324-V339 asset/CSP chain plus production settings: 174 tests passed in
  21.974 seconds.
- Final PostgreSQL regression: 3,039 tests passed in 458.389 seconds; measured
  wall-clock time was 480.6 seconds.
- Strict CLI with missing evidence: failed closed with seven blockers and no
  path or input echo.
- Passing strict CLI, schema tampering, extra fields, forged counts, unsafe
  origins, delivery failure, enforcement evidence, smoke mismatch, unreadable
  input, and oversized input: covered by focused tests.
- `manage.py check` and `manage.py check --tag templates`: zero issues.
- `makemigrations --check --dry-run`: no changes detected.
- `migrate --check --noinput`: passed without applying migrations.
- `collectstatic --dry-run --noinput`: passed.
- `git diff --check`: passed.
- No migration was created or applied; the development database was not
  mutated.

These tests were selected because V339 closes a multi-milestone security
operations lane: focused tests establish the new aggregator boundary, the
V324-V339 package proves adjacent CSP contracts remain aligned, and the full
suite is mandatory for a closeout checkpoint.

Checkpoint:
`project-checkpoint-v339-csp-observation-evidence-closeout`.

The selected follow-up is v340, a bounded CSP observation-window analysis
baseline that summarizes approved sanitized V337 evidence without raw report
access, network activity, persistence, or enforcement.
