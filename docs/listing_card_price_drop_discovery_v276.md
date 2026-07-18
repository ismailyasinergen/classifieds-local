# Listing Card Price-Drop Discovery — v276

## Purpose

v276 extends the v275 listing-price history feature from the detail page to
the shared listing card.

A buyer can now discover a current price reduction before opening the listing.

## Shared-card presentation

When the latest real price transition is a current reduction, the card shows:

- a **Price dropped** badge;
- the crossed-out previous price;
- the current listing price;
- the saving amount;
- the saving percentage when the previous price is greater than zero.

Baseline-only listings and listings whose latest transition is an increase do
not display a reduction.

## Current-transition safety

The latest transition's `new_price` must still equal the listing's persisted
current price.

This prevents a stale historical reduction from being exposed after a later
write that did not create a matching transition.

## Visibility boundary

Discovery is limited to listings that are:

- approved;
- not expired.

The feature does not broaden any existing listing visibility rule.

## N+1 prevention

The shared card uses a context-aware template tag.

On its first invocation, the tag gathers listing IDs from the current render
context, including:

- normal browse listings;
- seller-store pinned and regular listings;
- related listings;
- recently viewed listings;
- featured and latest home-page listings;
- category home-page sections;
- saved and account listings.

It then loads the latest price transitions for those IDs in one batch query
using correlated subqueries.

The result is cached on the request for the rest of the render. Rendering more
cards does not create one price-history query per card.

## Compatibility

v276 preserves:

- v271 related listings;
- v272 recently viewed listings;
- v273 public category navigation;
- v274 session-based comparison controls;
- v275 detail-page price history and price-drop presentation.

## Schema

v276 adds no model and no migration.

`0018_listingpricehistory` remains the latest listings migration.
