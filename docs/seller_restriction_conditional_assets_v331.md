# Seller-restriction conditional assets v331

## Outcome

V331 extracts the suspended-seller action rule and interaction handler from
`templates/base.html` into two versioned Accounts static assets:

- `accounts/static/accounts/seller-restriction-v331.css`
- `accounts/static/accounts/seller-restriction-v331.js`

Both assets remain conditional on `current_user_is_seller_suspended`. The CSS
link is placed after the existing `extra_styles` block, preserving the former
late cascade position. The JavaScript tag remains immediately after the
seller-restriction banner and before the shared top strip, and deliberately
does not use `defer`; its existing `DOMContentLoaded` registration and
interaction behavior are unchanged.

Unrestricted users receive neither V331 asset. Suspended sellers continue to
receive the restriction banner and reason, and both assets are loaded exactly
once.

## Extraction integrity

The normalized V330 conditional CSS payload is 157 characters and 6 lines.
V331 locks it with this SHA-256 digest:

`7266beb4c43015bb1cbea86b9cd779636e7a4d3d8ab13090a73edea3b762fc2d`

The normalized conditional JavaScript payload is 1,325 characters and 45
lines. V331 locks it with this SHA-256 digest:

`77f453094769dcfe929f49d0563a896e36f7187d825c2000dcf251d90e76d5a6`

Neither payload contains Django template tokens. Django's static finder
resolves both assets from `/app/accounts/static`.

## Audit boundary

The listing-detail/full-page asset audit now reports:

- five physical static assets: three CSS and two JavaScript;
- zero inherited inline style blocks;
- one inherited inline script block, the dynamic SEO JSON-LD payload;
- zero inline event handlers and zero inline style attributes;
- listing-detail-owned and template-level CSP readiness remain true;
- full-page `strict_csp_ready` remains false because JSON-LD is dynamic and
  inline.

The V331 marker is included in the audit's static-asset inventory, and the
text/JSON audit serializers lock the same counts.

## Validation

- V331 focused package: 10 tests passed in 10.111 seconds.
- Combined V324-V331 asset/CSP package: 65 tests passed in 67.177 seconds.
- Accounts, Pages, Deals, listing-detail, SEO, accessibility, and shared-shell
  compatibility package: 181 tests passed in 16.074 seconds.
- Final PostgreSQL regression: 2,933 tests passed in 422.206 seconds; measured
  wall-clock time was 443.4 seconds.
- `manage.py check` and `manage.py check --tag templates`: zero issues.
- `makemigrations --check --dry-run`: no changes detected.
- `findstatic` uniquely resolved both V331 assets.
- `collectstatic --dry-run --noinput`: passed.
- `audit_listing_detail_assets_v324`: five static assets, zero inherited
  styles, one inherited script, and `strict_csp_ready=false`.
- `git diff --check`: passed.
- No migration was created or applied; the development database was not
  mutated.

Checkpoint: `project-checkpoint-v331-seller-restriction-conditional-assets`.

The selected follow-up is v332, request-scoped CSP nonce groundwork for the
remaining dynamic SEO JSON-LD boundary without enabling an enforcement header
prematurely.
