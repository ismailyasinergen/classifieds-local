# Saved-Search Price-Drop Notifications (v286)

Saved searches now treat a listing's latest valid current reduction as
notification activity. This applies when canonical saved parameters include
`price_drops=1`, a valid `price_drop_period`, a valid minimum drop amount or
percentage, or `sort=recent_price_drop` / `sort=biggest_price_drop`. Ordinary
saved searches remain creation-based.

The matcher routes candidates through the shared v278–v282 public filter and
sort dispatcher, so saved-search execution and email matching use the same
current-reduction, period, threshold, and deterministic qualification rules.
For a price-drop search, a listing qualifies for the notification window when
it was created after `last_notification_checked_at` or its latest valid current
reduction occurred after that watermark. Reductions at or before the watermark,
stale history, later increases, current-price mismatches, expired listings, and
invalid filter values do not create price-drop activity.

Preview ordering uses the latest of listing creation and valid reduction time,
then primary key descending. Email copy says “new or newly reduced” only for
price-drop searches; existing copy remains unchanged for ordinary searches.
The existing dry-run, recipient validation, successful-send timestamp update,
delivery failure handling, saved-search ownership, and audit pipeline are
preserved.

The implementation adds no schema migration or dependency. It uses shared
database annotations and no per-listing history queries. PostgreSQL may still
inline correlated latest-history expressions; production-scale plans remain a
documented R004 measurement item. Durable cross-worker event deduplication is
reserved for v287.
