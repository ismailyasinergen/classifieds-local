# Base stylesheet static asset v330

## Outcome

V330 extracts the main shared `templates/base.html` style block into
`pages/static/pages/base-v330.css`. The template now loads the asset once with
Django's `{% static %}` tag immediately before the existing `extra_styles`
extension point.

The extraction changes no selector, declaration, media query, or cascade
ordering. It removes only the eight-space template indentation and adds the
`BASE_STYLESHEET_STATIC_ASSET_V330` asset marker.

## Extraction integrity

The normalized V329 payload is 19,725 characters and 1,118 lines. V330 locks it
with this SHA-256 digest:

`3a1b33b3c20919209371fa2c978ab4475a068272bd28db6bd8f9fc2471e05b42`

The CSS contains no Django template tokens. `findstatic` resolves
`pages/base-v330.css` uniquely from `/app/pages/static`, and a home-page response
verifies that its link appears once inside the document head.

## Audit boundary

The listing-detail/full-page asset audit now reports:

- three physical static assets: two CSS and one JavaScript;
- one inherited inline style block, the conditional seller-action rule;
- two inherited inline script blocks, JSON-LD and seller restriction handling;
- zero inline event handlers and zero inline style attributes;
- listing-detail-owned CSP readiness remains true;
- full-page `strict_csp_ready` remains false.

## Compatibility repairs

The extraction exposed two legacy tests that passed by finding CSS text inside
the old HTML response rather than verifying their intended UI behavior:

- The admin navigation smoke test now checks the rendered grouped-toolbar
  marker and the V330 stylesheet link instead of a CSS comment.
- The card-highlight test now uses generic browse rather than the specialized
  `cars` table route, asserts the listing is present in response context, and
  checks the exact rendered highlight class plus its four values.

The V237 navigation contract now anchors its staff-guard ordering check to the
actual grouped-toolbar HTML marker. V299, V322, and V329 source contracts read
the new base CSS asset for style-owned assertions.

## Validation

- V330 focused package: 8 tests passed.
- Combined V324-V330 asset/CSP package: 55 tests passed.
- Deals, listing-detail, seller, Pages, and shared-shell compatibility package:
  158 tests passed.
- Admin smoke/V236/V237/V330 repair package: 54 tests passed.
- Card-highlight package: 3 tests passed.
- The first two complete-suite attempts exposed the two legacy false-positive
  contracts above; both root causes were repaired and retested.
- Final PostgreSQL regression: 2,923 tests passed in 423.915 seconds; measured
  wall-clock time was 444.3 seconds.
- `manage.py check` and `manage.py check --tag templates`: zero issues.
- `makemigrations --check --dry-run`: no changes detected.
- `findstatic pages/base-v330.css --verbosity 2`: unique asset found.
- `collectstatic --dry-run --noinput`: passed.
- `git diff --check`: passed.
- No migration was created or applied; the development database was not
  mutated.

Checkpoint: `project-checkpoint-v330-base-stylesheet-static-asset`.

The selected follow-up is v331, extraction of the conditional seller-action
style and script while preserving suspension-only loading and behavior.
