# Pricing-Integrity Moderation Queue (v294)

## Behavior

Staff can inspect restricted price transitions at
`/staff/pricing-integrity/`. The interface is read-only: it does not suspend,
archive, approve, or otherwise change a listing. Anonymous users are redirected
to sign in and authenticated non-staff users receive a permission denial.

The queue contains `ListingPriceHistory` rows whose durable v293 guardrail state
restricts public discount promotion. It shows the listing, seller username,
listing status and category, previous and new prices, the pre-increase reference
price, the recorded time, and a human-readable restriction label. Email
addresses, price-change reasons, raw model fields, event IDs, and private notes
are not rendered.

## Current and historical evidence

A restriction is **current** only when its row is the latest non-baseline price
transition and its new price equals the listing's current price. Earlier flagged
rows and current-price mismatches remain available as historical evidence. This
classification never rewrites price history.

Filters support current/historical state, listing status, a stable operator
restriction value, and bounded title/seller-username search. Invalid filter
values are ignored safely. Results are ordered by `changed_at` descending and
primary key descending, then paginated in database-backed pages of 25.

## Architecture and operations

The focused queryset service uses one correlated subquery to identify the latest
non-baseline transition and `select_related` for listing, seller, and category.
Rendering therefore does not add a query per result. The PostgreSQL plan has not
yet been benchmarked with production-scale history cardinality.

No endpoint accepts moderation actions in v294. A future adjudication workflow
must define status, audit, notification, and appeal policy before enforcement is
added. v294 adds no model, migration, dependency, or public endpoint.
