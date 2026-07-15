# v245 — Saved-Search Notification Production Delivery Operational Readiness

## Checkpoint identity

- Base:
  `project-checkpoint-v244-saved-search-notification-production-delivery-operational-readiness-contract`
- Target:
  `project-checkpoint-v245-saved-search-notification-production-delivery-operational-readiness`
- Marker:
  `V245_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATIONAL_READINESS`

## Purpose

v245 implements the read-only operational-readiness preflight defined by v244.

It allows an operator to determine whether the existing saved-search
production-delivery configuration is ready without sending email, rendering an
email, connecting to a provider, querying or mutating the database, writing an
audit event or changing notification timestamps.

## Exact v245 scope

v245 modifies exactly:

1. `backend/listings/saved_search_notification_production_readiness.py`
2. `backend/listings/management/commands/check_saved_search_notification_production_readiness.py`
3. `backend/listings/test_saved_search_notification_production_delivery_operational_readiness_v245.py`
4. `docs/saved_search_notification_production_delivery_operational_readiness_v245.md`

## Readiness service

The public service is:

`get_saved_search_notification_production_readiness()`

It returns a deterministic structured result with:

- `marker`
- `status`
- `ready`
- `checks`
- `ready_count`
- `not_ready_count`
- `warning_count`

Every check contains:

- `check_id`
- `status`
- `passed`
- `reason_code`

No raw setting value is returned.

## Implemented readiness checks

The implementation verifies:

1. The production-delivery feature gate is declared.
2. The feature gate is enabled.
3. An email backend is configured.
4. The configured backend is not locmem, dummy, console or file-based.
5. A default sender is configured.
6. Both explicit production-confirmation controls remain packaged.
7. Positive owner scoping remains packaged.
8. An explicit bounded limit remains packaged.
9. The production batch maximum remains 25.

## Default behavior

The local development configuration reports `not_ready` safely because the
production-delivery feature gate defaults to disabled.

The report is informational by default and does not fail the management
command.

## Management command

The command is:

`python manage.py check_saved_search_notification_production_readiness`

Supported options:

- `--strict`
- `--json`

Default mode prints a sanitized human-readable report.

`--json` prints the same sanitized structured result as JSON.

`--strict` raises `CommandError` when readiness is not complete.

Strict mode remains report-only and performs no delivery or mutation.

## Read-only boundary

The readiness service and command do not:

- Import saved-search models.
- Query the database.
- Insert, update or delete rows.
- Write persistent audit events.
- Render notification email content.
- Construct an email message.
- Open an email connection.
- Contact SMTP or another provider.
- Read provider credentials.
- Execute the production delivery function.
- Modify scheduler behavior.

## Privacy boundary

Output contains only:

- Stable marker
- Overall readiness status
- Boolean readiness state
- Stable check identifiers
- Stable reason codes
- Aggregate counts

Output never contains:

- Email backend path
- Default sender value
- Recipient addresses
- Saved-search names
- Saved-search querystrings
- Rendered subjects or bodies
- SMTP usernames or passwords
- API keys or tokens
- Provider response bodies
- Raw exception text

## Existing delivery boundary

v245 does not modify:

- Production-delivery feature-gate settings.
- The production sender.
- The production delivery management command.
- Scheduler behavior.
- Persistent audit services.
- Timestamp rollback behavior.
- Models.
- Admin.
- URLs.
- Templates.
- Database migrations.

The latest listings migration remains:

`0016_savedsearchnotificationauditevent`

Migration `0017` remains absent.

## Validation

The checkpoint validates:

- Default development configuration reports not-ready.
- A valid production-like override reports ready.
- Known nonproduction backends are rejected.
- Missing default sender is rejected.
- Results are deterministic.
- Human output is sanitized.
- JSON output is sanitized.
- Strict mode fails closed.
- Non-strict mode reports normally.
- No email connection is opened.
- No database access or mutation occurs.
- Existing production-delivery and audit safeguards remain green.
- The complete regression suite remains green.

## Next checkpoint

v246: saved-search notification production delivery operational readiness closeout audit
