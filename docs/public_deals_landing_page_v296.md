# v296 — Public Deals Landing Page

## Purpose

v296 adds a public, paginated Deals page at `/deals/`. The page exposes only
currently public listings with a genuine, current, promotable price reduction.

## Eligibility contract

The page does not define a new discount algorithm. It reuses the established
v278–v284 price-drop pipeline.

A listing appears only when:

- existing approved and unexpired public-visibility rules allow it;
- its latest non-baseline price-history transition is a reduction;
- the previous price is present and greater than zero;
- the transition's new price equals the listing's persisted current price;
- the v293 public discount guardrail status is clear.

Consequently, the page excludes baseline-only listings, stale reductions,
later increases, no-op transitions, current-price mismatches, zero or missing
previous prices, guarded raise-then-drop transitions, expired listings, and
all non-public listing statuses.

## Ordering

Deals use the existing v281 deterministic biggest-discount ordering:

1. discount percentage descending;
2. discount amount descending;
3. valid reduction time descending;
4. listing primary key descending.

All calculations and ordering are performed through database expressions.

## Presentation and accessibility

The page reuses the shared `_listing_card.html` partial and therefore preserves:

- listing detail links and images;
- v284 previous/current price, saving, and percentage presentation;
- favorites and comparison actions;
- seller-store presentation;
- responsive listing-card layout.

The page has one visible `Deals` heading, labelled result sections, an accessible
pagination navigation landmark, and no nested `<main>` element.

## Performance and privacy

The queryset applies public visibility before discount qualification and uses
related-object loading for category, owner, profile, seller store, and images.

The existing v276 card discovery cache performs one batched price-drop lookup
for all cards in the rendered page. It does not perform one history query per
card.

No private pricing-integrity metadata, guardrail reference price, recipient
state, or moderation data is added to the public response.

## Schema impact

v296 introduces no model changes and no migration. Migration
`0023_listingpricehistory_discount_guardrail_v293` remains the latest listings
migration.

## Validation scope

Focused v296 tests cover public access, navigation, card evidence, eligibility
exclusions, v293 guardrails, deterministic ordering, pagination, semantic
markup, stable query count, compatibility markers, and absence of a v296
migration.

Related v276, v281, v284, and v293 tests should run before the complete serial
`--keepdb` regression suite.
