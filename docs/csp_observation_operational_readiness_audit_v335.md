# CSP observation operational-readiness audit v335

## Outcome

V335 adds a deterministic, read-only management command for deciding whether
the built-in V333/V334 CSP observation path has all required application and
operator evidence:

```text
python manage.py check_csp_observation_readiness_v335
python manage.py check_csp_observation_readiness_v335 --json
python manage.py check_csp_observation_readiness_v335 --strict
```

The command performs no network access, report emission, cache or database
write, file write, or CSP enforcement. Text and JSON output contain only fixed
check identifiers, status values, reason codes, counts, and the V335 marker.
Strict mode fails closed unless all 13 checks pass.

## Readiness contract

The audit verifies:

- both V333/V334 settings exist and both observation gates are enabled;
- the Report-Only policy targets the exact built-in
  `/__csp_reports__/` path;
- the Report-Only middleware remains outside the nonce middleware;
- the built-in path still resolves to the V334 ingestion view;
- configured logging can deliver the sanitized V334 `INFO` event;
- a packaged synthetic legacy payload parses into the exact privacy-bounded
  evidence schema without retaining paths, queries, samples, or tokens;
- an edge rate limit has been independently reviewed;
- sanitized log retention, access, and export controls have been independently
  reviewed;
- a real same-origin synthetic report delivery has been independently
  verified;
- the middleware still references only the Report-Only header and no
  enforcement setting exists.

Default local configuration returns seven ready checks and six blockers:
Report-Only disabled, ingestion disabled, built-in URI not selected, edge
limit not approved, log governance not approved, and synthetic delivery not
verified.

## Operator attestations

V335 introduces three independently default-off audit settings:

```text
DJANGO_CSP_OBSERVATION_EDGE_RATE_LIMIT_APPROVED=0
DJANGO_CSP_OBSERVATION_LOG_GOVERNANCE_APPROVED=0
DJANGO_CSP_OBSERVATION_SYNTHETIC_REPORT_VERIFIED=0
```

They do not configure an edge, log platform, or smoke test. Operators may set
one to `1` only after reviewing the corresponding external control or
evidence. This prevents repository source inspection from overclaiming
production readiness.

The synthetic delivery must use non-sensitive invented values, return `204`,
reach the approved sanitized `security.csp_report_v334` log destination, and
show no `Content-Security-Policy` enforcement header. A real account, URL,
token, policy, or script sample must not be used.

## Validation

- V335 focused package: 12 tests passed in 0.179 seconds.
- V324-V335 asset/CSP chain plus production settings: 125 tests passed in
  72.618 seconds.
- Final PostgreSQL regression: 2,990 tests passed in 423.491 seconds; measured
  wall-clock time was 445.0 seconds.
- Default command JSON: seven ready and six not-ready checks, read-only true.
- Reviewed production-like strict audit: 13 of 13 checks ready.
- `manage.py check` and `manage.py check --tag templates`: zero issues.
- `makemigrations --check --dry-run`: no changes detected.
- `migrate --check --noinput`: passed without applying migrations.
- `collectstatic --dry-run --noinput`: passed.
- `git diff --check`: passed.
- No migration was created or applied; the development database was not
  mutated.

Checkpoint: `project-checkpoint-v335-csp-observation-readiness-audit`.

The selected follow-up is v336, a CSP report edge abuse-control baseline with
an exact-path request limit, endpoint-specific body bound, proxy configuration
validation, and no change to CSP enforcement or report persistence.
