# v231 — Saved-Search Notification Audit Runtime Integration Contract

## Checkpoint identity

- Base checkpoint:
  `project-checkpoint-v230-saved-search-notification-audit-persistence-write-service`
- Target checkpoint:
  `project-checkpoint-v231-saved-search-notification-audit-runtime-integration-contract`
- Marker:
  `V231_SAVED_SEARCH_NOTIFICATION_AUDIT_RUNTIME_INTEGRATION_CONTRACT`
- Next implementation:
  `v232: saved-search notification audit runtime integration implementation`

## Purpose

v231 defines how the persistent audit model and append-only write service will
be connected to the existing saved-search notification runtime.

This checkpoint is contract-only.

It does not yet modify scheduler, renderer, sender, rollback, management
command, model, migration, email configuration, templates, or Django admin.

## Proposed runtime adapter

Future module:

`listings/saved_search_notification_audit_runtime.py`

Future public API:

- `SavedSearchNotificationAuditRuntimeContext`
- `record_saved_search_notification_runtime_event`
- `build_saved_search_notification_audit_idempotency_key`
- `build_saved_search_notification_fingerprint`

The adapter will be the only new runtime-facing entry point to the v230
persistence service.

Existing runtime modules must not:

- Instantiate `SavedSearchNotificationAuditEvent` directly.
- Call its manager directly.
- Generate ad hoc idempotency keys.
- Generate ad hoc fingerprints.
- Bypass metadata privacy validation.
- Swallow persistence exceptions.

## Runtime integration targets

- `listings/saved_search_notification_scheduler.py`
- `listings/saved_search_notification_email_renderer.py`
- `listings/saved_search_notification_email_sender.py`
- `listings/saved_search_notification_audit.py`
- `listings/management/commands/process_saved_search_notifications.py`

## Runtime context

### Correlation ID

One UUID identifies one explicit single-search execution or one management
command invocation.

All audit events produced by that execution reuse the same `correlation_id`.

### Batch ID

One optional UUID identifies one multi-search batch.

Every saved search processed by that batch uses the same `batch_id`.

### Delivery attempt ID

A new UUID is created immediately before each backend send attempt.

The following events reuse the same `delivery_attempt_id`:

- `delivery_attempted`
- `delivery_succeeded`
- `delivery_failed`
- `sent_timestamp_recorded`

A retry receives a new attempt ID.

### Actor identity

Allowed actor types remain:

- `scheduler`
- `management_command`
- `operator`
- `test_backend`
- `system`

`actor_identifier` may contain only a stable, non-secret operational label.

It must not contain credentials, tokens, email addresses, cookies, sessions,
tracebacks, or rendered content.

### Source

`source` is a stable dotted identifier for the runtime surface producing the
event.

Examples:

- `saved_search.scheduler.evaluate`
- `saved_search.renderer.preview`
- `saved_search.sender.test_backend`
- `saved_search.command.process`
- `saved_search.rollback.preview`
- `saved_search.rollback.apply`

## Event integration matrix

### `evaluation_started`

- Outcome: `pending`
- Surface: scheduler
- Trigger: immediately before evaluating one persisted saved search
- Required context:
  - `correlation_id`
  - `notification_fingerprint`
  - `checked_at_before`

This event does not mutate notification timestamps.

### `skipped_notifications_disabled`

- Outcome: `skipped`
- Surface: scheduler
- Trigger: an explicitly selected saved search is disabled
- Required context:
  - `correlation_id`
  - `notification_fingerprint`
  - normalized `reason_code`

### `skipped_missing_recipient`

- Outcome: `skipped`
- Surface: sender precondition
- Trigger: delivery is requested but no usable recipient exists
- Required context:
  - `correlation_id`
  - `notification_fingerprint`
  - normalized `reason_code`

The recipient address itself must not be persisted in metadata.

### `dry_run_rendered`

- Outcome: `succeeded`
- Surface: renderer
- Trigger: explicit preview or dry-run rendering completes
- Required metadata:
  - `mode`
  - `match_count`
  - `rendered_item_count`

No subject, body, HTML, text, listing title, listing description, or private URL
may be persisted.

### `delivery_attempted`

- Outcome: `pending`
- Surface: sender
- Trigger: immediately before invoking the email backend
- Required context:
  - `correlation_id`
  - `delivery_attempt_id`
  - `notification_fingerprint`

This event must commit successfully before the backend send begins.

If it cannot be persisted, delivery is aborted.

### `delivery_succeeded`

- Outcome: `succeeded`
- Surface: sender
- Trigger: backend send reports success
- Required context:
  - `correlation_id`
  - `delivery_attempt_id`
  - `notification_fingerprint`

This event records the external delivery result.

It does not itself mutate `last_notification_sent_at`.

### `delivery_failed`

- Outcome: `failed`
- Surface: sender
- Trigger: backend send raises or reports failure
- Required context:
  - `correlation_id`
  - `delivery_attempt_id`
  - `notification_fingerprint`
  - stable `reason_code`

Metadata may contain a normalized `error_code`.

Metadata must not contain exception messages, tracebacks, stack traces, SMTP
responses containing addresses, or credentials.

A failed delivery never changes `last_notification_sent_at`.

### `sent_timestamp_recorded`

- Outcome: `succeeded`
- Surface: management command orchestration
- Trigger: `last_notification_sent_at` is persisted after successful delivery
- Required context:
  - `correlation_id`
  - `delivery_attempt_id`
  - `notification_fingerprint`
  - `sent_at_before`
  - `sent_at_after`

The timestamp mutation and audit event must be written in the same database
transaction.

If the audit write fails, the timestamp mutation must roll back.

### `rollback_previewed`

- Outcome: `succeeded`
- Surface: rollback audit helper
- Trigger: explicit rollback preview is generated
- Required context:
  - `correlation_id`
  - `notification_fingerprint`
  - `rollback_of`

Preview is read-only.

`rollback_of` targets the original `sent_timestamp_recorded` event.

### `rollback_applied`

- Outcome: `rolled_back`
- Surface: rollback audit helper
- Trigger: explicit rollback restores a sent timestamp
- Required context:
  - `correlation_id`
  - `notification_fingerprint`
  - `rollback_of`
  - `sent_at_before`
  - `sent_at_after`

The restored timestamp and `rollback_applied` event must be written in the same
database transaction.

If audit persistence fails, the timestamp restoration must roll back.

## Required event ordering

The implementation must preserve these relationships:

1. `evaluation_started` precedes render or delivery processing.
2. `delivery_attempted` precedes backend send invocation.
3. Exactly one backend result event follows one attempt:
   - `delivery_succeeded`, or
   - `delivery_failed`.
4. `delivery_succeeded` precedes `sent_timestamp_recorded`.
5. `delivery_failed` never produces `sent_timestamp_recorded`.
6. `rollback_previewed` may precede `rollback_applied`.
7. `rollback_applied` must reference the original
   `sent_timestamp_recorded` event.

Event ordering is represented by shared correlation, attempt, rollback, and
occurrence fields rather than by rewriting earlier events.

## Idempotency key contract

Prefix:

`ssna:v1:`

Algorithm:

`sha256`

The digest input is canonical JSON with:

- Sorted keys.
- Compact separators.
- NaN disabled.
- UTF-8 encoding.

Identity fields:

- `saved_search_id`
- `event_type`
- `correlation_id`
- `batch_id`
- `delivery_attempt_id`
- `rollback_of_id`
- `operation_sequence`

The final key must remain within the model’s 128-character limit.

The same normalized identity and payload must produce the same key.

An identical replay returns the original row with:

`created=False`

A mismatched replay raises:

`SavedSearchNotificationAuditIdempotencyConflict`

## Notification fingerprint contract

Algorithm:

`sha256`

Canonical fields:

- `saved_search_id`
- Saved-search path
- Saved-search query string
- `checked_at_before`
- Ordered matching listing IDs

For skipped or zero-match paths, ordered matching IDs are an empty sequence.

One delivery chain reuses one fingerprint across:

- `dry_run_rendered`
- `delivery_attempted`
- `delivery_succeeded`
- `delivery_failed`
- `sent_timestamp_recorded`

Rollback events inherit the fingerprint from the original
`sent_timestamp_recorded` event.

## Metadata allowlist

### Evaluation

Allowed:

- `mode`
- `owner_scope`
- `batch_position`

### Skipped events

Allowed:

- `mode`
- `skip_reason`

### Dry-run rendering

Allowed:

- `mode`
- `match_count`
- `rendered_item_count`

### Delivery events

Allowed:

- `mode`
- `match_count`
- `backend_kind`
- `error_code` for failures only

### Sent timestamp

Allowed:

- `mode`
- `timestamp_changed`

### Rollback preview

Allowed:

- `mode`
- `preview_count`

### Rollback apply

Allowed:

- `mode`
- `timestamp_changed`

## Metadata privacy exclusions

The runtime integration must never persist:

- Recipient email addresses.
- Email subject lines.
- Rendered bodies.
- Rendered HTML.
- Rendered plain text.
- Listing titles or descriptions.
- Private listing URLs.
- Raw exception messages.
- Tracebacks or stack traces.
- SMTP credentials or responses containing private data.
- Authentication or authorization values.
- Cookies or session identifiers.
- Access, API, refresh, or private tokens.
- Secret keys.

## Transaction boundaries

### Before delivery

`delivery_attempted` must commit before the email backend is called.

Failure to persist this event aborts delivery.

### After delivery

Email delivery is an external side effect and cannot be rolled back by a
database transaction.

After the backend reports success:

1. Persist `delivery_succeeded`.
2. Mutate `last_notification_sent_at`.
3. Persist `sent_timestamp_recorded` in the same database transaction as the
   timestamp mutation.

### Delivery failure

On backend failure:

1. Persist `delivery_failed`.
2. Do not mutate `last_notification_sent_at`.
3. Propagate or report the delivery failure through the existing explicit
   command result path.

### Rollback apply

The restored timestamp and `rollback_applied` event must be committed in the
same database transaction.

## Failure semantics

### Pre-delivery audit failure

- Abort delivery.
- Do not invoke the email backend.
- Do not mutate timestamps.
- Propagate the audit error.

### Backend delivery failure

- Write `delivery_failed`.
- Do not write `delivery_succeeded`.
- Do not write `sent_timestamp_recorded`.
- Do not mutate the sent timestamp.

### Post-delivery audit failure

The system must surface an indeterminate delivery state.

It must retain the `delivery_attempt_id`.

It must not automatically retry, because the external email may already have
been delivered.

### Timestamp audit failure

The timestamp mutation must roll back.

### Rollback audit failure

The timestamp restoration must roll back.

### Idempotency conflict

Propagate:

`SavedSearchNotificationAuditIdempotencyConflict`

Conflicts must never be silently converted into successful results.

### Exception visibility

Audit persistence exceptions must never be silently ignored.

No broad `except Exception: pass` behavior is permitted.

## Default behavior safeguards

v232 must preserve these existing safeguards:

- Default management-command execution does not deliver email.
- Explicit execution remains required for test-backend sending.
- Non-locmem backend protections remain active.
- Production delivery remains disabled.
- No scheduler auto-delivery is introduced.
- No background worker is introduced.
- No retry worker is introduced.
- Owner scope and batch limit protections remain active.
- Missing-recipient paths remain non-crashing.
- One failed saved search does not silently corrupt later searches.
- Saved-search timestamp semantics remain explicit.

## Adapter ownership boundary

Only the proposed runtime adapter may import:

`record_saved_search_notification_audit_event`

Scheduler, renderer, sender, rollback, and command modules call the runtime
adapter rather than the persistence service directly.

This centralizes:

- Context normalization.
- Fingerprint construction.
- Idempotency-key construction.
- Event ordering inputs.
- Actor/source mapping.
- Metadata allowlists.
- Failure reporting.

## Explicit exclusions

v231 does not:

- Create the runtime adapter.
- Modify scheduler behavior.
- Modify rendering behavior.
- Modify sender behavior.
- Modify rollback behavior.
- Modify the management command.
- Deliver email.
- Enable production delivery.
- Add automatic scheduling.
- Add retries.
- Add a background worker.
- Add editable audit admin.
- Add model fields.
- Add migration `0017`.
- Change email settings.
- Change templates.
- Create `backend/docs`.

## Acceptance gates for v232

- Runtime adapter is the only persistence-facing integration API.
- Runtime modules do not instantiate audit model rows directly.
- Runtime modules do not call the audit model manager directly.
- Runtime modules do not generate ad hoc keys or fingerprints.
- All ten event types have covered trigger paths.
- `delivery_attempted` is durable before sending.
- One attempt has one success or failure result.
- Failed delivery never changes the sent timestamp.
- Sent timestamp mutation and event are atomic.
- Rollback timestamp restoration and event are atomic.
- Identical integration replay creates no duplicate event.
- Conflicting replay fails explicitly.
- Metadata remains allowlisted and privacy-minimized.
- No sensitive payload enters metadata.
- Default command behavior remains non-delivery.
- Production delivery remains disabled.
- No background worker is introduced.
- No model or migration change is generated.
- Existing saved-search notification tests remain green.
- Full regression remains green.

## Next checkpoint

v232: saved-search notification audit runtime integration implementation
