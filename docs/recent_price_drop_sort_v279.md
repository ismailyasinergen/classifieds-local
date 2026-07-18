# v279 — Recently Reduced Browse Sort

v279 adds the public browse sort:

`sort=recent_price_drop`

## Behaviour

- Returns only listings whose latest non-baseline price transition is a real reduction.
- Requires the transition's new price to match the listing's current price.
- Orders matching listings by reduction time descending, then listing ID descending.
- Works on the main public listing browse and category listing pages.
- Preserves the v278 `price_drops=1` filter.
- Supports active-filter labels, pagination, and saved searches.
- Adds the “Recently reduced” option to the public sort menu.

## Data and migrations

The feature uses `ListingPriceHistory` and adds no database migration.
