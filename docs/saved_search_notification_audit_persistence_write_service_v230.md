# v230 — Saved-Search Notification Audit Persistence Write Service

## Checkpoint identity

- Base checkpoint:
  `project-checkpoint-v229-saved-search-notification-audit-persistence-model-migration`
- Target checkpoint:
  `project-checkpoint-v230-saved-search-notification-audit-persistence-write-service`
- Marker:
  `V230_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_WRITE_SERVICE`
- Runtime module:
  `listings.saved_search_notification_audit_persistence`

## Purpose

v230 implements the append-only persistence service defined by the v228
contract and backed by the v229 model and migration.

The service creates or safely replays individual audit events. It does not
connect the model to scheduler, rendering, delivery, rollback execution,
management commands, or Django admin.

## Public API

### Write function

`record_saved_search_notification_audit_event`

The function:

- Requires a persisted `SavedSearch`.
- Derives `owner_id_snapshot` from `saved_search.user_id`.
- Validates event, outcome, and actor choices.
- Requires timezone-aware timestamps.
- Normalizes UUID string inputs.
- Requires a 64-character hexadecimal notification fingerprint.
- Validates rollback linkage.
- Validates delivery-attempt linkage.
- Canonicalizes privacy-safe JSON metadata.
- Uses `transaction.atomic`.
- Uses `get_or_create` by `idempotency_key`.
- Returns the existing row for an identical replay.
- Raises an explicit conflict for a mismatched replay.
- Never rewrites an existing event.

### Result type

`SavedSearchNotificationAuditWriteResult`

Fields:

- `event`
- `created`

The result dataclass is frozen.

### Conflict type

`SavedSearchNotificationAuditIdempotencyConflict`

The exception exposes:

- `idempotency_key`
- `differing_fields`

## Idempotency behavior

### First write

A new idempotency key creates one audit row and returns:

`created=True`

### Identical replay

The same idempotency key with the same normalized payload returns the original
row and:

`created=False`

No duplicate event is created.

### Conflicting replay

The same idempotency key with a different normalized payload raises:

`SavedSearchNotificationAuditIdempotencyConflict`

The existing audit event remains unchanged.

## Replay comparison fields

- `saved_search_id`
- `owner_id_snapshot`
- `event_type`
- `outcome`
- `reason_code`
- `occurred_at`
- `batch_id`
- `correlation_id`
- `delivery_attempt_id`
- `notification_fingerprint`
- `rollback_of_id`
- `actor_type`
- `actor_identifier`
- `source`
- Notification timestamp snapshots
- `metadata`

Generated primary key and insertion timestamp are not replay inputs.

## Metadata privacy boundary

Metadata must be a JSON object with string keys.

The recursive key validator rejects sensitive data categories including:

- Authorization values.
- Authentication headers.
- Cookies and sessions.
- Access, API, and refresh tokens.
- Passwords and SMTP passwords.
- Secrets and private keys.
- Rendered email bodies.
- Rendered HTML or text.
- Tracebacks and stack traces.

Non-JSON values are rejected before insertion.

Metadata key ordering is canonicalized so semantically identical dictionaries
remain replay-safe.

## Rollback validation

The following event types require `rollback_of`:

- `rollback_previewed`
- `rollback_applied`

The referenced event must:

- Already exist.
- Be a `SavedSearchNotificationAuditEvent`.
- Belong to the same saved search.

## Delivery-attempt validation

The following event types require `delivery_attempt_id`:

- `delivery_attempted`
- `delivery_succeeded`
- `delivery_failed`

## Timestamp safety

The service stores timestamp snapshots only inside the audit event.

It never mutates:

- `SavedSearch.last_notification_checked_at`
- `SavedSearch.last_notification_sent_at`

## Delivery safety

The service:

- Does not import Django mail.
- Does not call an email sender.
- Does not render an email.
- Does not invoke the scheduler.
- Does not execute a management command.
- Does not add a background worker.

## Database boundary

v230 adds no model fields and no migration.

The latest listings migration remains:

`0016_savedsearchnotificationauditevent`

## Historical transition guards

The v228 contract test now permits the persistence module once the v230 test
module is packaged.

The v229 model/migration test now permits the persistence module once the v230
test module is packaged.

The historical pre-v230 absence assertions remain active when the v230 test
module is absent.

## Explicit exclusions

v230 does not:

- Integrate audit writes into scheduler evaluation.
- Integrate audit writes into email preview rendering.
- Integrate audit writes into test-backend sending.
- Integrate audit writes into rollback execution.
- Change the management command.
- Add production delivery.
- Add retries or asynchronous workers.
- Add editable admin registration.
- Add an audit browser page.
- Change notification settings.
- Change notification templates.
- Mutate saved-search timestamps.
- Create migration `0017`.
- Create `backend/docs`.

## Acceptance gates

- First write returns `created=True`.
- Identical replay returns `created=False`.
- Identical replay returns the same row.
- Conflicting replay raises the explicit conflict exception.
- Conflicting replay does not mutate the original row.
- Choice values are validated.
- UUIDs and fingerprints are validated.
- Rollback linkage is validated.
- Delivery-attempt linkage is validated.
- Sensitive metadata is rejected recursively.
- Non-JSON metadata is rejected.
- The write executes inside `transaction.atomic`.
- The service uses `get_or_create` by `idempotency_key`.
- No email is delivered.
- Saved-search timestamps remain unchanged.
- No model or migration change is generated.
- Existing audit, saved-search, and notification tests remain green.
- Full regression remains green.

## Next checkpoint

v231: saved-search notification audit runtime integration contract
