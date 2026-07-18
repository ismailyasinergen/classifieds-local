# Public Price-History Timeline (v283)

The public listing-detail page shows a **Price history** section when a listing
has meaningful recorded transitions. It uses the existing listing-detail route
and therefore preserves its anonymous, owner, and staff visibility rules.

## Eligibility and ordering

The query includes rows for the viewed listing only when `previous_price` and
`new_price` are present and different. Baseline creation rows and equal-price
no-ops are excluded. Historical increases and reductions remain eligible even
when later transitions exist.

Results are ordered by `changed_at` descending and primary key descending, then
limited to the latest 20 rows in SQL. The timeline uses one bounded query; the
existing v275 current-price summary reuses those fetched rows, avoiding a
second history query or per-entry N+1 work.

## Display values

Reductions use `previous_price - new_price`; increases use
`new_price - previous_price`. The absolute value is always non-negative.
Percentage change is calculated with `Decimal` as
`absolute_change / previous_price * 100` when `previous_price > 0`, displayed
to useful precision without unnecessary trailing zeros. A zero previous price
renders **Percentage unavailable** instead of attempting division.

Only the newest eligible transition is marked **Current price**, and only when
its `new_price` equals the listing's current price. Dates use the project's
localized display convention plus an ISO-compatible `<time datetime>` value.

## Privacy and schema

The template exposes only prices, absolute and percentage changes, direction,
date/time, and the optional current marker. It does not expose row IDs, actors,
audit data, administrative links, or internal metadata. v283 adds no endpoint,
dependency, model change, or database migration. Production-scale history
queries remain subject to normal query-plan monitoring despite the existing
listing/time index and strict 20-row limit.
