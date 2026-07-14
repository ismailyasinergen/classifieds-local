# v232 — Saved-Search Notification Audit Runtime Integration

## Checkpoint identity

- Base:
  `project-checkpoint-v231-saved-search-notification-audit-runtime-integration-contract`
- Target:
  `project-checkpoint-v232-saved-search-notification-audit-runtime-integration-implementation`
- Marker:
  `V232_SAVED_SEARCH_NOTIFICATION_AUDIT_RUNTIME_INTEGRATION`

## Purpose

v232 connects the v229 persistent append-only model and the v230 replay-safe
write service to the existing saved-search notification runtime.

The integration preserves the existing preview, locmem test-backend delivery,
rollback, command, and production-safety guardrails.

## Central runtime adapter

Module:

`listings.saved_search_notification_audit_runtime`

Public API:

- `SavedSearchNotificationAuditRuntimeContext`
- `build_saved_search_notification_fingerprint`
- `build_saved_search_notification_audit_idempotency_key`
- `record_saved_search_notification_runtime_event`
- `find_latest_saved_search_notification_sent_event`

Only this adapter imports the v230 persistence service.

Scheduler, renderer, sender, rollback, and management-command modules do not
call the persistence service or audit-event manager directly.

## Context identity

One runtime context carries:

- Correlation UUID.
- Optional batch UUID.
- Actor type.
- Actor identifier.
- Stable source.
- Aware start timestamp.
- Runtime mode.

Derived surface contexts preserve correlation, batch, actor, and start time.

## Fingerprint

The SHA-256 notification fingerprint uses canonical JSON containing:

- Saved-search ID.
- Stored path.
- Stored query string.
- Checked timestamp before evaluation.
- Ordered matching-listing IDs.

One preview or delivery chain reuses the same fingerprint.

Rollback events inherit the original sent-timestamp event fingerprint.

## Idempotency key

Prefix:

`ssna:v1:`

The SHA-256 identity includes:

- Saved-search ID.
- Event type.
- Correlation ID.
- Batch ID.
- Delivery-attempt ID.
- Rollback target ID.
- Stable operation sequence.

An already-recorded delivery attempt is rejected before the email backend is
invoked again.

## Scheduler and renderer

Preview execution now records:

1. `evaluation_started`
2. `dry_run_rendered`

Explicit disabled-search preview attempts record:

`skipped_notifications_disabled`

Preview execution still:

- Sends no email.
- Does not mutate checked timestamps.
- Does not mutate sent timestamps.
- Preserves owner and limit filtering.

## Sender

Explicit locmem test-backend delivery now records:

1. `delivery_attempted`
2. Exactly one of:
   - `delivery_succeeded`
   - `delivery_failed`
3. After success:
   - `sent_timestamp_recorded`

Missing-recipient execution records:

`skipped_missing_recipient`

`delivery_attempted` commits before the email backend is called.

Backend exceptions persist a normalized error code only. Raw messages,
tracebacks, credentials, recipient addresses, subjects, and rendered bodies are
not written to persistent metadata.

## Timestamp transaction

After successful external delivery:

1. `delivery_succeeded` is persisted.
2. `last_notification_sent_at` is updated.
3. `sent_timestamp_recorded` is persisted in the same database transaction as
   the timestamp update.

If the timestamp audit event fails, the database timestamp mutation rolls back.

Because email delivery is external, a failure after successful backend delivery
is surfaced rather than automatically retried.

## Rollback

Read-only rollback reports may persist:

`rollback_previewed`

only when a persistent `sent_timestamp_recorded` target exists.

Explicit rollback persists:

`rollback_applied`

with `rollback_of` pointing to the original sent-timestamp event.

Timestamp restoration and `rollback_applied` are committed in one database
transaction.

Legacy rollback behavior remains available for old rows that predate persistent
sent-timestamp audit events.

## Management command

The command creates one shared runtime context per invocation.

The same correlation and batch identity are passed to:

- Email preview execution.
- Explicit locmem test-backend delivery.
- Persistent rollback preview.

Default command execution remains non-delivery.

## Privacy

Runtime metadata is event-specific and allowlisted.

Persistent metadata never stores:

- Recipient email addresses.
- Email subjects.
- Rendered HTML or text.
- Listing titles or descriptions.
- Raw exception messages.
- Tracebacks or stack traces.
- Credentials, cookies, sessions, or tokens.

## Preserved safety boundaries

v232 does not:

- Enable production email delivery.
- Add automatic scheduling.
- Add a background worker.
- Add a retry worker.
- Change email settings.
- Change email templates.
- Register editable audit admin.
- Change the audit model.
- Create migration `0017`.
- Create `backend/docs`.

## Acceptance gates

- Adapter is the only persistence-facing runtime API.
- Deterministic keys and fingerprints are stable.
- Preview produces evaluation and render events.
- Disabled and missing-recipient paths produce skip events.
- Attempt commits before send.
- Success and failure result events are mutually exclusive.
- Failed delivery does not update the sent timestamp.
- Sent timestamp mutation and event are atomic.
- Rollback timestamp restoration and event are atomic.
- Duplicate attempt replay does not resend.
- Metadata remains privacy-minimized.
- Existing locmem test-backend gate remains active.
- Default command remains non-delivery.
- No model or migration change is generated.
- Full regression remains green.

## Next checkpoint

v233: saved-search notification persistent audit operator read-interface contract
