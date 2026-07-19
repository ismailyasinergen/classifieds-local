# v299 - Deals discovery integration and release-readiness audit

## Purpose

v299 completes the public discovery integration for the Deals experience
introduced in v296 and extended through v297 and v298.

It does not introduce a second Deals route, a new price-drop calculation, a
model field, or a database migration.

## Main navigation integration

The shared header continues to resolve the Deals destination through the
existing `safe_url` helper.

On `listings:public_deals_v296`, the Deals navigation link receives:

- `aria-current="page"`;
- a versioned active-state class;
- a visible selected treatment.

Browse, comparison, and other routes retain the Deals link without marking it
as the current page.

## Keyboard and responsive behavior

Shared header links and menu summaries now have an explicit `:focus-visible`
treatment.

The existing responsive contract remains unchanged. At 720 pixels and below,
the navigation continues to use the full width and its links keep their
flexible sizing.

## Discovery continuity

The release audit verifies that:

- Deals links back to the complete public listing browser;
- listing comparison links into Deals discovery;
- header navigation, URL resolution, and canonical metadata use the same Deals
  route identity.

## Release-readiness coverage

The v299 audit preserves the established sprint contracts:

- v296 pagination and per-card query stability;
- v297 comparison query stability and Deals CTAs;
- v298 canonical metadata, JSON-LD packaging, zero-query checks, and shared
  template fallback behavior;
- anonymous and authenticated header rendering;
- no new route, model, or migration.

## Deliberate exclusions

v299 does not add personalized recommendations, tracking parameters, sitemap
or robots endpoints, a new pricing algorithm, model changes, or migrations.
