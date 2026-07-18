# Price-drop period filter v280

Version 280 adds `price_drop_period` to public listing browse URLs. Accepted
values are `24h`, `7d`, and `30d`; missing or invalid values leave the queryset
unrestricted by time.

The shared v280 helper reads the latest non-baseline `ListingPriceHistory`
transition. A listing qualifies only when that transition reduced the price,
its `new_price` still equals the listing's current price, and its timezone-aware
`changed_at` value is on or after the selected inclusive cutoff. The existing
`price_drops=1` filter and `sort=recent_price_drop` use the same annotation set,
avoiding repeated transition subqueries when parameters are combined.

Both `/listings/` and category listing pages inherit the behavior through the
shared public sorter. The public filter form offers Any time, Last 24 hours,
Last 7 days, and Last 30 days. Pagination, active-filter chips, and saved-search
canonicalization preserve valid values. Saved-search cleaning drops invalid
periods before persistence.

No model or schema changes are required for v280.
