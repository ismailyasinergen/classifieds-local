# Base-template inline-style attribute cleanup v329

## Outcome

V329 removes all three inline `style=` attributes from `templates/base.html`.
The seller-suspension banner, Django message container, and individual message
now use these dedicated classes in the existing main base CSS block:

- `seller-restriction-banner-v329`
- `django-message-list-v329`
- `django-message-v329`

All former declarations are preserved, including banner colors, spacing,
alignment and weight plus message spacing, border, radius, and background. The
rules sit at the end of the main base style block after existing responsive
rules, giving the new, unique selectors a stable cascade position.

## CSP boundary

The inherited base-template inventory is now:

- two inline style blocks;
- two inline script blocks;
- zero inline event handlers;
- zero inline style attributes.

Listing-detail-owned strict-CSP readiness remains true. Full-page
`strict_csp_ready` intentionally remains false until the shared style and script
blocks are extracted. Text and JSON audit outputs both expose the zero
inherited-inline-style result.

## Compatibility

The focused suite renders `base.html` with both an active seller restriction
and a Django message. It verifies that the banner reason and message text remain
visible through the replacement classes and that the rendered HTML contains no
inline style attribute.

The previous v328 audit expectations were advanced from three inherited inline
style attributes to zero; its two-style/two-script blocker contract remains
unchanged.

## Validation

- V329 focused package: 8 tests passed.
- Combined V324-V329 asset/CSP package: 47 tests passed.
- Seller, shared-shell, navigation, listing-detail SEO/accessibility, and audit
  compatibility package: 149 tests passed.
- Full PostgreSQL regression: 2,915 tests passed in 429.447 seconds; measured
  wall-clock time was 450.8 seconds.
- `manage.py check` and `manage.py check --tag templates`: zero issues.
- `makemigrations --check --dry-run`: no changes detected.
- `collectstatic --dry-run --noinput`: passed.
- `git diff --check`: passed.
- No migration was created or applied; the development database was not
  mutated.

Checkpoint: `project-checkpoint-v329-base-inline-style-attribute-cleanup`.

The selected follow-up is v330, exact extraction of the main shared base CSS
block into a versioned static asset while preserving the `extra_styles` cascade
boundary.
