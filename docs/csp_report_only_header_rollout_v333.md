# CSP Report-Only header rollout v333

## Outcome

V333 adds an environment-controlled `Content-Security-Policy-Report-Only`
response header that consumes the request-scoped nonce introduced in V332.
Rollout is disabled by default:

```text
DJANGO_CSP_REPORT_ONLY_ENABLED=0
DJANGO_CSP_REPORT_ONLY_REPORT_URI=
```

When enabled, the outermost `CspReportOnlyMiddlewareV333` adds the observation
policy to final Django responses, including HTML, health, early media-block,
and custom 405 responses. It never emits a `Content-Security-Policy`
enforcement header. A Report-Only header supplied by an upstream proxy or
platform is preserved unchanged.

## Policy contract

The deterministic policy contains:

- `default-src 'self'`;
- `base-uri 'self'`;
- `object-src 'none'`;
- `frame-ancestors 'none'`;
- `form-action 'self'`;
- `script-src 'self' 'nonce-<request-nonce>'`;
- `script-src-attr 'none'`;
- `style-src 'self' 'unsafe-inline'`;
- `img-src 'self' data: blob:`;
- `font-src 'self' data:`;
- `connect-src 'self'`;
- `media-src 'self' blob:`;
- `frame-src 'none'`;
- `worker-src 'self' blob:`;
- `manifest-src 'self'`.

The optional legacy `report-uri` directive is appended only when an approved
collector is configured. The URI must be either a same-origin absolute path or
a credential-free HTTPS URI. Control characters, whitespace, non-ASCII text,
header delimiters, quotes, backslashes, protocol-relative URLs, fragments,
credentials, and cleartext external collectors are rejected.

No report ingestion endpoint, persistence, logging, rate limiting, or
enforcement switch is introduced in V333.

## Transitional source inventory

The repository-wide template inventory records:

- 10 templates containing inline script blocks;
- 18 templates containing inline style blocks;
- 9 templates containing inline event handlers;
- 41 templates containing inline style attributes;
- 4 `URL.createObjectURL` uses for local image/video previews;
- zero external script, stylesheet, image, media, or iframe subresource
  origins;
- one nonce-aware template, the shared `templates/base.html` JSON-LD block.

This evidence explains the deliberately transitional policy:

- `style-src 'unsafe-inline'` prevents the existing inline-style estate from
  generating an unbounded report flood;
- nonce-free inline scripts and event handlers remain disallowed by the
  observation policy and will generate violations;
- `data:` and `blob:` are limited to resource families used by current local
  previews;
- the OpenStreetMap URL is a user navigation link, not a loaded subresource,
  and therefore is not added to the allow-list.

## Operations

Both environment examples and `README_PRODUCTION.md` document the default-off
rollout. Operators may enable browser-console observation with an empty report
URI or configure an approved same-origin/HTTPS collector. Collected violations
must be reviewed before any policy or enforcement change.

An existing upstream Report-Only header remains authoritative, preventing two
deployment layers from silently replacing each other's policy.

## Validation

- V333 focused package: 15 tests passed in 3.510 seconds.
- V332/V333, production settings, Pages, seller, Deals, listing-detail SEO,
  accessibility, release-audit, and V324-V331 compatibility package: 151 tests
  passed in 25.521 seconds.
- Final PostgreSQL regression: 2,959 tests passed in 429.959 seconds; measured
  wall-clock time was 454.2 seconds.
- `manage.py check` and `manage.py check --tag templates`: zero issues.
- Enabled rollout check with a same-origin report URI: zero issues.
- `makemigrations --check --dry-run`: no changes detected.
- `collectstatic --dry-run --noinput`: passed.
- `git diff --check`: passed.
- No migration was created or applied; the development database was not
  mutated.

Checkpoint: `project-checkpoint-v333-csp-report-only-header-rollout`.

The selected follow-up is v334, a bounded and sanitized CSP violation-report
ingestion foundation for same-origin deployment evidence without enforcement.
