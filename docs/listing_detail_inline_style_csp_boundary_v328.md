# Listing-detail inline-style and CSP boundary cleanup v328

## Outcome

V328 removes all four listing-detail-owned inline `style=` attributes. One
comparison layout and three repeated section panels now use two classes in the
existing `listing-detail-v324.css` static asset.

The replacement rules are intentionally placed after the generic section-panel
rules. This preserves the precedence previously supplied by inline styles for
`border-top` and `border-radius`; a source-order regression test protects that
contract.

## CSP boundary

The v324 audit now reports two explicit scopes:

- `template_owned_strict_csp_ready=true`: `listing_detail.html` has no inline
  style blocks, script blocks, event handlers, or style attributes.
- `strict_csp_ready=false`: the complete rendered page still inherits two
  style blocks, two script blocks, zero inline event handlers, and three inline
  style attributes from `templates/base.html`.

This distinction prevents the listing-detail extraction from overstating
full-page CSP readiness. The audit remains deterministic and read-only, reports
two static assets and sixteen asset-aware source-contract consumers, and finds
no remaining listing-detail extraction blockers.

## Compatibility repair

The v274 comparison source contract now checks for the preserved
`listing-comparison-detail-v274` class token instead of requiring it to be the
only class in the attribute. Its form method, CSRF, return target, and action
security assertions are unchanged.

## Validation

- V324-V328 focused package: 39 tests passed.
- Related compatibility package: 174 tests passed.
- Full PostgreSQL regression: 2,907 tests passed in 419.216 seconds; measured
  wall-clock time was 440.8 seconds.
- `manage.py check` and `manage.py check --tag templates`: zero issues.
- `makemigrations --check --dry-run`: no changes detected.
- `collectstatic --dry-run --noinput`: passed.
- `git diff --check`: passed.
- No migration was created or applied; the development database was not
  mutated.

Checkpoint: `project-checkpoint-v328-listing-detail-inline-style-csp-boundary`.

The selected follow-up is v329, a bounded cleanup of the three inherited
`base.html` inline style attributes before larger shared style/script block
extraction work.
