# v301 — Notification scheduler leasing

## Purpose

v301 prevents overlapping notification scheduler processes from repeating
candidate matching and email-preparation work.

Durable v287 logical-event claims remain the delivery correctness boundary.
The scheduler lease is an operational efficiency guard and does not replace
event-level deduplication, retry limits, preferences, or terminal event states.

## Lease mechanism

The implementation uses PostgreSQL session advisory locks with stable,
versioned two-part integer keys.

This design provides:

- atomic non-blocking acquisition;
- no scheduler lease table;
- no persistent stale lease rows;
- automatic release when the PostgreSQL session closes or crashes;
- token-free, recipient-free operator coordination;
- independent locks for listing-price alerts and saved-search notifications.

## Protected command modes

The listing-price-alert command acquires its lease only when `--send` is used.

The `check_saved_search_notifications` command acquires its lease when
either:

- `--send` is used; or
- `--mark-checked` is used.

The mature `process_saved_search_notifications` command uses the same
saved-search lease for:

- confirmed `--execute-production-send`;
- `--execute-email-send`; and
- timestamp-mutating `--execute`.

Its default dry-run, email-preview, observability-report, and rollback-report
paths do not acquire a scheduler lease. Existing argument and production-policy
validation runs before lease acquisition.

Default read-only dry runs do not acquire a scheduler lease.

When a lease is already held, the command exits without candidate scanning,
email delivery, event claiming, or timestamp mutation and prints a sanitized
operator message.

## Preserved contracts

v301 preserves:

- v287 notification event identity and atomic claim behavior;
- v288 notification preference suppression;
- per-item failure isolation;
- dry-run defaults;
- existing command arguments and validation order;
- cross-command coordination between both saved-search command surfaces;
- recipient-sanitized output;
- the current PostgreSQL deployment contract.

## Deliberate exclusions

v301 adds no route, model, admin surface, migration, background worker,
provider integration, verified-email policy, event-retention policy, or
automatic retry policy.

## Validation evidence

The completed v301 validation recorded:

- 16 focused scheduler-lease tests passing;
- 140 related notification compatibility tests passing;
- 2,657 complete regression tests passing in 1233.694 seconds;
- Django system check with zero issues;
- migration dry-run reporting `No changes detected`;
- listings migration `0023_listingpricehistory_discount_guardrail_v293` still
  serving as the migration head;
- the local development and preserved test databases observed fully migrated
  through listings migration `0023`.

v301 did not run `migrate` against the development database.
