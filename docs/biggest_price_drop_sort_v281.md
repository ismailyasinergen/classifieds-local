# Biggest Price Drop Sort (v281)

Public listing and category browse pages accept the exact query value
`sort=biggest_price_drop`, displayed as **Biggest discount**. The sort includes
only listings whose latest non-baseline price transition is a reduction and
whose transition price still equals the listing's current price. The previous
price must also be greater than zero.

The database annotates each qualifying listing with:

```text
discount_amount = previous_price - current_price
discount_percentage = (discount_amount / previous_price) * 100
```

Results are ordered by discount percentage descending, discount amount
descending, latest valid reduction time descending, and listing primary key
descending. Decimal database expressions preserve fractional percentages and
stable ordering without per-listing Python work.

The sort reuses v278 current-reduction qualification, v279 public sort
dispatch, and v280 period filtering. It combines with `price_drops=1` and all
supported `price_drop_period` values. Pagination and saved searches preserve
the exact sort value, while active-filter summaries use the public label.

No model or schema change is required, so v281 adds no migration. The query
continues to rely on indexed correlated latest-transition subqueries; this
avoids application-level N+1 queries, but production-scale query plans should
still be monitored.
