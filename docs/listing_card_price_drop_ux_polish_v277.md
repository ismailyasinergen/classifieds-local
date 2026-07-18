# Listing Card Price-Drop UX and Accessibility Polish — v277

## Purpose

v277 improves the buyer-facing presentation introduced by v276.

v276 already determines whether a listing's latest real price transition is a
current reduction and batches those lookups across the shared listing-card
render context.

v277 does not replace or duplicate that calculation. It improves the shared
card's semantics, clarity, testability, and assistive-technology output.

## Buyer-facing changes

For a listing with a valid current price reduction, the shared card now shows:

- the existing **Price dropped** badge;
- the previous price with a specific accessible label;
- a visible **Now** label beside the current price;
- **You save** wording instead of the less descriptive **Save** wording;
- the saving amount;
- the saving percentage when v276 supplies one.

Baseline-only listings, stale transitions, and listings whose latest
transition is an increase do not receive the v277 presentation.

## Accessibility contract

The price-drop summary is exposed as a labeled group.

Its accessible label identifies both:

- the previous price;
- the current price.

The current price and saving summary also receive explicit accessible labels.

The visible badge includes explanatory title text without introducing a new
interactive control.

## Stable test hooks

v277 adds narrowly scoped HTML data attributes for regression testing:

- `data-price-drop-card-v277`;
- `data-price-drop-badge-v277`;
- `data-previous-price-v277`;
- `data-current-price-v277`;
- `data-saving-amount-v277`;
- `data-saving-percentage-v277`;
- `data-price-drop-saving-copy-v276`.

The final compatibility attribute preserves the original v276 literal saving
copy for existing regression contracts while the visible buyer-facing wording
remains **You save**.

These attributes expose only values already shown publicly on the listing
card. They do not expose private seller, buyer, or audit information.

## Compatibility

v277 preserves:

- v274 session-based listing comparison;
- v275 detail-page price history;
- v276 current-transition validation;
- v276 request-level batch caching;
- all current listing visibility rules;
- all public, seller-store, saved-listing, account, and home-page card
  surfaces.

The shared card still calls the v276 context-aware template tag. No additional
price-history query is introduced by v277.

## Scope

v277 modifies only:

1. `backend/listings/templates/listings/_listing_card.html`;
2. `backend/listings/test_listing_card_price_drop_ux_polish_v277.py`;
3. `docs/listing_card_price_drop_ux_polish_v277.md`.

## Schema

v277 adds:

- no model;
- no migration;
- no database field;
- no URL;
- no view;
- no form;
- no background task.

`0018_listingpricehistory` remains the latest listings migration.
