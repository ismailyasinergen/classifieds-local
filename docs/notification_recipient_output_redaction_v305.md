# v305 — Legacy operator recipient-output redaction migration

## Purpose

v305 implements R010 by migrating the four legacy recipient-bearing
operator-output surfaces identified by the v304 notification-delivery policy
baseline.

The milestone changes operator presentation only. It does not alter email
address selection, rendered email context, sender destination payloads,
scheduler candidate selection or delivery-event identity.

## Shared redaction contract

The shared implementation module is:

    listings.notification_recipient_output_redaction_v305

Configured recipient addresses are represented as:

    [redacted]

Unavailable or blank recipient values are represented as:

    <missing>

The helper is idempotent:

- `[redacted]` remains `[redacted]`;
- `<missing>` remains `<missing>`;
- blank values become `<missing>`;
- every other value becomes `[redacted]`.

## Migrated operator surfaces

The following four v304 inventory entries are migrated together:

- explicit saved-search email-send command results;
- saved-search email preview command output;
- saved-search observability sample structures and text;
- saved-search rollback-plan structures and text.

The v304 executable policy discovery now reports:

- operator recipient-output policy: `redacted_by_default`;
- remaining legacy recipient-output surfaces: zero;
- operator recipient-output readiness: ready;
- remaining blocking capabilities: three.

The remaining blockers are verified-recipient state, provider delivery outcomes
and notification-event retention.

## Preserved delivery boundary

v305 intentionally leaves these delivery-internal files unchanged:

- `saved_search_notification_email_renderer.py`;
- `saved_search_notification_email_sender.py`;
- `saved_search_notification_scheduler.py`.

Actual destination addresses remain available to the delivery pipeline where
required. Only operator-facing output is redacted.

## Deliberate exclusions

v305 adds no:

- model or schema migration;
- email-verification lifecycle;
- provider integration or webhook;
- bounce or complaint handling;
- retention deletion or archival automation;
- route, template or admin change;
- background worker;
- development-database mutation;
- runtime delivery-enforcement change.

## Validation evidence

The completed v305 validation recorded:

- 6 focused v305 tests passing;
- 1,380 saved-search notification tests passing;
- 67 policy and delivery compatibility tests passing;
- policy text and JSON output reporting zero legacy recipient-output surfaces;
- policy discovery reporting R010 ready and exactly three blockers remaining;
- strict policy mode continuing to fail while those three blockers remain;
- shared redaction-helper idempotence;
- configured recipients rendering as `[redacted]`;
- missing recipients rendering as `<missing>`;
- no raw recipient expression remaining in the four operator surfaces;
- delivery renderer, sender and scheduler files unchanged;
- Django system checks reporting zero issues;
- `makemigrations --check --dry-run` reporting no changes;
- `migrate --check --noinput` passing read-only;
- the complete parallel regression discovering and running
  2,691 tests;
- explicit full-suite `OK` in 398.842 seconds;
- 420 seconds measured wall-clock time;
- no `FAILED` summary;
- listings migration head remaining
  `0023_listingpricehistory_discount_guardrail_v293`.

v305 did not run `migrate` against the development database. It adds no model,
schema migration, email-verification workflow, provider integration, retention
automation, background worker or delivery-enforcement change.
