# Listing-Specific Price Alerts (v285)

Authenticated buyers can enable or disable a price alert from an approved,
unexpired listing detail page. Owners cannot subscribe to their own listings.
Each subscription stores the listing price at opt-in and is unique per
user/listing pair; subscription state is private and is never rendered for
another user.

`check_listing_price_alerts` is dry-run by default. `--send` delivers email in a
bounded batch of at most 100 alerts. A candidate must now be below its opt-in
price and its latest non-baseline history transition must be a valid current
reduction: the prior price is positive and greater than the new price, and the
new price equals the listing's current price. Pending, expired, stale,
increased, or already-notified current prices are excluded. State advances only
after a successful send; missing recipients and delivery failures remain
retryable.

The query reuses the shared v278 latest-transition annotations inside one
correlated eligibility expression and loads users and listings with
`select_related`, avoiding per-alert queries. The detail page adds one private
existence query for an eligible authenticated buyer and no query for anonymous,
owner, invalid-price, or non-public views.

The existing detail visibility path is unchanged, POST actions remain CSRF
protected, and return URLs use the R001 same-origin validator. Email includes
only public listing title, prices, and detail URL. Migration `0019` adds the
subscription table; it does not rewrite listing or history data. Robust
cross-worker delivery-event deduplication remains planned for v287.
