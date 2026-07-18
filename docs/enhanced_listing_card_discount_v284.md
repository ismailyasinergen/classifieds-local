# Enhanced Listing-Card Discount Presentation (v284)

Public listing cards now present a valid current reduction as concise buyer
evidence: the current price remains prominent, the previous price uses semantic
`<del>` markup, and the card states the absolute saving and discount percentage.
Visible direction, price labels, and complete ARIA explanations ensure that the
discount is not communicated by color alone.

## Qualification and formatting

v284 delegates latest-transition discovery to the existing batched v276
service. That service already requires the latest non-baseline transition to be
a reduction whose new price equals the listing's current price. The v284
presentation wrapper adds the percentage-specific requirement that the previous
price be greater than zero. Baseline-only, no-op, stale, mismatched, increased,
and zero-base states therefore retain the normal card price presentation.

Amounts remain `Decimal` values. The v276 calculation provides the absolute
saving and percentage, while the shared v282 decimal formatter removes
unnecessary percentage trailing zeros (`10.00` becomes `10`; `16.67` remains
`16.67`). No binary floating-point calculations are introduced.

## Integration and performance

The shared `_listing_card.html` is used by browse, category, search, seller
store, related, recently viewed, favorites, and dashboard surfaces, so links,
images, titles, locations, promotion badges, and responsive behavior remain in
the existing component. The v284 wrapper is in-memory presentation work over
the single v276 batched query and introduces no per-card database access.

v284 adds no endpoint, dependency, model change, or database migration. The
existing correlated history subqueries remain subject to production query-plan
monitoring for unusually large card collections.
