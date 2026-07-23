# Dynamic SEO JSON-LD CSP nonce groundwork v332

## Outcome

V332 establishes request-scoped CSP nonce plumbing for the remaining dynamic
SEO JSON-LD block without emitting or enforcing a Content Security Policy.

`config.csp_nonce_v332.CspNonceMiddlewareV332` creates a 256-bit URL-safe nonce
before view and template processing. The dedicated context processor exposes
the same value as `csp_nonce_v332`, and `templates/base.html` renders JSON-LD
only when both the serialized payload and nonce are present:

```html
<script type="application/ld+json" nonce="{{ csp_nonce_v332 }}">
```

The nonce is stable within one request, distinct across requests, and has a
43-character `[A-Za-z0-9_-]` representation. Non-SEO pages still receive the
request context but render no JSON-LD script.

## Deliberate enforcement boundary

V332 does not emit either `Content-Security-Policy` or
`Content-Security-Policy-Report-Only`. Real response tests lock this boundary
for SEO and non-SEO pages. Policy authoring, source allow-list review, reporting
destinations, browser observation, and eventual enforcement remain separate
rollout decisions.

The JSON-LD serializer and its script-breakout escaping are unchanged. The
nonce is presentation metadata and is not persisted, logged, or reused across
requests.

## Audit evolution

The v324 asset audit now records `has_csp_nonce` for inline script blocks and
separates:

- `nonce_protected_script_blocks`;
- `unprotected_script_blocks`.

The inherited base boundary contains one inline JSON-LD script, one
nonce-protected script, and zero unprotected scripts. It continues to contain
zero inline styles, event handlers, or style attributes. Consequently the
template/source boundary reports `strict_csp_ready=true`, while response tests
independently prove that enforcement remains disabled.

Text audit output now includes:

- `inherited_scripts=1`;
- `inherited_nonce_scripts=1`;
- `inherited_unprotected_scripts=0`;
- `strict_csp_ready=true`.

## Compatibility

The V298 Deals SEO assertions now identify the JSON-LD script by content type
rather than requiring an exact opening tag without attributes. JSON payload,
canonical metadata, script-breakout safety, listing-detail SEO, Pages,
seller-restriction, and all earlier V324-V331 asset contracts remain intact.

## Validation

- V332 focused package: 11 tests passed in 8.419 seconds.
- Combined V324-V332 asset/CSP package: 76 tests passed in 65.797 seconds.
- Existing V298 SEO package: 12 tests passed in 1.193 seconds.
- Production settings, Pages, seller, Deals, listing-detail SEO,
  accessibility, release-audit, and V324-V332 compatibility package: 136 tests
  passed in 22.652 seconds.
- Final PostgreSQL regression: 2,944 tests passed in 416.722 seconds; measured
  wall-clock time was 437.8 seconds.
- `manage.py check` and `manage.py check --tag templates`: zero issues.
- `makemigrations --check --dry-run`: no changes detected.
- `collectstatic --dry-run --noinput`: passed.
- `audit_listing_detail_assets_v324`: one nonce-protected script, zero
  unprotected scripts, and `strict_csp_ready=true`.
- `git diff --check`: passed.
- No migration was created or applied; the development database was not
  mutated.

Checkpoint: `project-checkpoint-v332-dynamic-seo-json-ld-csp-nonce`.

The selected follow-up is v333, an environment-controlled CSP Report-Only
header rollout that consumes the same request nonce without enabling
enforcement.
