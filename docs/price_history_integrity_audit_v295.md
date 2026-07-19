# Price-History Integrity Audit (v295)

## Purpose

v295 adds a read-only operational audit for `ListingPriceHistory`. It detects
data consistency problems without changing listing prices, historical rows,
guardrail states, or moderation outcomes.

Run the audit after applying committed migrations:

```bash
docker compose exec -T web python manage.py audit_listing_price_history_integrity
docker compose exec -T web python manage.py audit_listing_price_history_integrity --json
docker compose exec -T web python manage.py audit_listing_price_history_integrity --fail-on-findings
```

`--max-findings` bounds printed details between 1 and 1,000 while total counts
remain complete. `--fail-on-findings` supports CI and operational health checks.

## Checks

The audit reports missing or misplaced baseline rows, multiple baselines,
broken transition chains, equal-price no-op rows, latest/current-price
mismatches, future timestamps, unsupported reason or guardrail values, and
malformed restricted evidence. Findings are ordered deterministically by
listing, transition time, and transition primary key.

## Privacy and performance

Text and JSON output contain finding codes plus listing and transition IDs for
operator correlation. They omit listing titles, usernames, email addresses,
price-change reasons, free text, and other user data. Output is bounded and no
public or staff web endpoint is added.

The service streams two ordered querysets—listings and price-history rows—using
fixed-size database chunks. Query count therefore remains two as data volume
grows, with no per-listing or per-transition queries. Production-scale scan
duration and query plans remain unbenchmarked.

## Safety and migration status

The command has no repair option and performs no writes. Findings must be
investigated before any manual correction; v295 does not define seller penalties
or moderation adjudication. No model change, dependency, or migration is added.
The target database must have existing migrations through v293 applied before
the audit can inspect the corresponding fields.
