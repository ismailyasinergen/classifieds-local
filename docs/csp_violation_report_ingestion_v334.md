# CSP violation-report ingestion foundation v334

## Outcome

V334 adds a bounded same-origin endpoint for receiving CSP violation evidence
from the V333 Report-Only policy:

```text
DJANGO_CSP_REPORT_ONLY_ENABLED=1
DJANGO_CSP_REPORT_ONLY_REPORT_URI=/__csp_reports__/
DJANGO_CSP_REPORT_INGESTION_ENABLED=1
```

The ingestion gate is independent and disabled by default. The route exists at
`/__csp_reports__/`, accepts `POST` only, and remains a non-persistent
observation surface. V334 does not emit a `Content-Security-Policy`
enforcement header or change application behavior in response to a report.

## Input and abuse bounds

The endpoint accepts only:

- `application/csp-report` with one legacy `csp-report` object;
- `application/reports+json` with one to ten `csp-violation` objects.

Requests are limited to 16 KiB. JSON must be valid UTF-8 and match the expected
media-type shape. A fixed-window cache limit allows 60 requests per hashed
client address per 60 seconds, before body parsing. The address itself is not
stored in the cache key.

The application cache limiter is defense in depth. With the default local
memory cache it is process-local, so production must also apply an approved
distributed rate limit at the reverse proxy or edge.

## Privacy and evidence contract

Accepted reports produce one structured `INFO` log event per violation on the
`security.csp_report_v334` logger. No database model, migration, file, or raw
payload persistence is introduced.

The fixed evidence schema retains only:

- media type and bounded report index;
- effective and violated directive tokens;
- report disposition and bounded status, line, and column numbers;
- document, blocked-resource, and source origins or safe resource classes.

URL paths, queries, fragments, credentials, wrapper URLs, original policies,
referrers, and script samples are discarded. Relative resources and CSP
keywords such as `inline`, `eval`, `data`, and `blob` are classified without
retaining their original text.

The route is CSRF-exempt because browser CSP reporters do not possess an
application CSRF token. It does not opt into cross-origin resource sharing.
Production log retention, access, alerting, and export controls remain an
operator responsibility.

## Response contract

- `404` while ingestion is disabled;
- `405` for non-POST methods;
- `415` for unsupported media types;
- `429` with `Retry-After` after the application limit;
- `413` for an oversized body;
- `400` for empty, unreadable, malformed, or invalid reports;
- `204` after sanitized evidence is logged.

Endpoint-generated responses use `Cache-Control: no-store`. Invalid requests
are not logged as violation evidence.

## Validation

- V334 focused package: 19 tests passed in 0.252 seconds.
- V332-V334, production settings, Pages, seller, Deals, listing-detail SEO,
  accessibility, release-audit, and V324-V331 compatibility package: 174 tests
  passed in 24.997 seconds.
- Final PostgreSQL regression: 2,978 tests passed in 426.936 seconds; measured
  wall-clock time was 448.8 seconds.
- `manage.py check` and `manage.py check --tag templates`: zero issues.
- Enabled V333/V334 rollout check with the same-origin ingestion path: zero
  issues.
- `makemigrations --check --dry-run`: no changes detected.
- `collectstatic --dry-run --noinput`: passed.
- `git diff --check`: passed.
- No migration was created or applied; the development database was not
  mutated.

Checkpoint: `project-checkpoint-v334-csp-violation-report-ingestion`.

The selected follow-up is v335, a read-only CSP observation
operational-readiness audit covering deployment gates, edge rate limiting,
sanitized log controls, synthetic report delivery, and continued absence of
enforcement.
