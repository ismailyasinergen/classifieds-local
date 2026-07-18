# Minimum Price-Drop Filters (v282)

Public listing and category browse pages accept
`min_price_drop_amount` and `min_price_drop_percent`. Values must be plain,
finite decimals greater than zero. Amounts support the listing-price precision
of two decimal places; percentages retain up to ten decimal places. Empty,
zero, negative, comma-formatted, non-finite, malformed, and oversized values
are ignored without activating price-drop qualification.

Active filters reuse the latest non-baseline transition and current-reduction
rules from v278-v281. The previous price must be positive, greater than the
transition price, and the transition price must equal the listing's current
price. Metrics are database annotations:

```text
discount_amount = previous_price - current_price
discount_percentage = (discount_amount / previous_price) * 100
```

Threshold comparisons are inclusive. When both parameters are valid, amount
and percentage filters use AND semantics. They combine with v278's price-drop
flag, v280 periods, v279 recent-drop ordering, v281 biggest-discount ordering,
regular sorts, and existing public/category filters.

Pagination, active-filter clearing, saved-search creation, summaries, and
saved-search execution preserve validated values. No model or schema change is
required, so v282 adds no migration. Filtering remains database-side and adds
no application-level N+1 work, although correlated latest-transition
subqueries should still be monitored with production-scale query plans.
