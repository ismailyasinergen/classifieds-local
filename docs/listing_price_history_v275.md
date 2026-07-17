# v275 — Listing Price History and Price-Drop Indicator

## Checkpoint identity

- Base commit:
  `f15561df4ac2039f00240ded41017d2689543feb`
- Base tag:
  `project-checkpoint-v274-listing-comparison`
- Target tag:
  `project-checkpoint-v275-listing-price-history`
- Marker:
  `LISTING_PRICE_HISTORY_V275`

## Purpose

v275 introduces persistent price history for marketplace listings.

Each listing receives one baseline entry representing its initial price.
Later entries are created only when the persisted price changes.

The public listing-detail page displays:

- The current price
- A price-drop badge when the latest current transition is a reduction
- The previous price
- The absolute saving
- The percentage reduction
- A bounded newest-first public price timeline

## Centralized capture

Price transitions are captured by the `Listing.save()` persistence path.

This covers:

- Seller listing creation
- Seller listing editing
- Django admin model saves
- Normal direct model saves

Price-history writes occur in the same database transaction as the listing
save. Existing listing rows are locked during price updates so concurrent
normal model saves observe a deterministic previous price.

Saves that explicitly exclude `price` through `update_fields` bypass the
history lookup. Saves with an unchanged price create no new transition.

Bulk queryset operations intentionally remain outside this model-save
contract. The inspected runtime contained no listing-price `QuerySet.update`
or `bulk_update` path.

## Data model

`ListingPriceHistory` stores:

- Listing
- Previous price
- New price
- Change timestamp

A baseline row has `previous_price = NULL`.

A conditional database constraint permits only one baseline row per listing.
Deleting a listing cascades to its history.

## Existing-data backfill

Migration `0018_listingpricehistory` creates one baseline entry for every
existing listing, using:

- The listing's current price
- The listing's original `created_at` timestamp

## Intentional migration-number reservation

Migration `0017` remains absent.

Historical v241 through v270 checkpoint tests explicitly assert that no
`0017*` migration exists. To preserve those committed compatibility
contracts, v275 advances directly from migration 0016 to migration 0018.

Django migration numbering does not require contiguous numeric prefixes;
the explicit dependency remains:

`0016_savedsearchnotificationauditevent`

## Privacy and visibility

The public timeline exposes only listing prices and change timestamps.

It does not expose:

- Editor identity
- Administrative notes
- Seller email
- Internal moderation data
- Request metadata
- IP data

## Compatibility boundary

v275 does not modify:

- Listing-detail view source
- CRUD view source
- Forms
- Admin configuration
- URLs
- Global views facade
- Category navigation
- Comparison service
- Related-listing service
- Recently-viewed service

The v271, v272, v273 and v274 features remain intact.

## Manual browser QA

1. Sign in as a seller.
2. Edit an existing listing.
3. Lower its price.
4. Open the listing-detail page.
5. Confirm the current price remains primary.
6. Confirm “Price dropped” appears.
7. Confirm the old price is struck through.
8. Confirm saving amount and percentage are correct.
9. Confirm the Price history timeline lists the transition.
10. Increase the price and confirm the drop badge disappears while the
    timeline retains both transitions.

## v274 price-box compatibility

The v274 comparison control remains inside the listing price box. v275 augments the existing current-price line and price-box opening without replacing or relocating the comparison form.

## Timeline independence from recommendations

The public price-history timeline is rendered independently from the v271 related-listings section. A listing with price changes shows its history even when no similar listings are available.
