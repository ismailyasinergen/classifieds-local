# v228 — Saved-Search Notification Audit Persistence Implementation Contract

## Checkpoint identity

- Marker:
  `V228_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_IMPLEMENTATION_CONTRACT`
- Base checkpoint:
  `project-checkpoint-v227-saved-search-notification-audit-persistence-design`
- Target checkpoint:
  `project-checkpoint-v228-saved-search-notification-audit-persistence-implementation-contract`
- Checkpoint type: implementation contract only
- Model and migration implementation: explicitly deferred to v229

## Purpose

v227 established the audit-persistence design.

v228 converts that design into an exact implementation contract covering:

- The Django model name.
- The migration name and dependency.
- The complete field schema.
- Stable event, outcome, and actor choices.
- Database indexes and check constraints.
- Append-only model behavior.
- The isolated persistence write service.
- Idempotent replay behavior.
- Metadata privacy validation.
- Implementation acceptance tests.

v228 does not yet create the model, migration, persistence module, audit rows,
admin interface, scheduler integration, delivery integration, rollback
integration, or retention enforcement.

## Required v229 artifacts

The model and migration implementation checkpoint must provide:

1. `SavedSearchNotificationAuditEvent` in `listings/models.py`.
2. Migration:
   `listings/migrations/0016_savedsearchnotificationauditevent.py`.
3. Migration dependency:
   `("listings", "0015_savedsearch_notifications")`.
4. Persistence module:
   `listings/saved_search_notification_audit_persistence.py`.
5. Focused model, migration, append-only, replay, and privacy tests.

## Exact model field contract

### `id`

- Django type: `UUIDField`
- Options:
  - `primary_key=True`
  - `default=uuid.uuid4`
  - `editable=False`

### `saved_search`

- Django type: `ForeignKey`
- Target: `SavedSearch`
- `on_delete=models.PROTECT`
- `related_name="notification_audit_events"`

Historical audit events must not disappear because a saved search deletion is
attempted.

### `owner_id_snapshot`

- Django type: `CharField`
- `max_length=64`
- Required

The value is an immutable string snapshot of the owner identifier at event
creation time. It is not used as an authentication credential.

### `event_type`

- Django type: `CharField`
- `max_length=64`
- Choices: `EventType.choices`

Required values:

1. `evaluation_started`
2. `skipped_notifications_disabled`
3. `skipped_missing_recipient`
4. `dry_run_rendered`
5. `delivery_attempted`
6. `delivery_succeeded`
7. `delivery_failed`
8. `sent_timestamp_recorded`
9. `rollback_previewed`
10. `rollback_applied`

Existing values must not be renamed or silently redefined.

### `outcome`

- Django type: `CharField`
- `max_length=32`
- Choices: `Outcome.choices`

Required values:

- `pending`
- `skipped`
- `succeeded`
- `failed`
- `rolled_back`

### `reason_code`

- Django type: `CharField`
- `max_length=96`
- `blank=True`

Reason codes are stable machine-readable identifiers, not arbitrary prose or
exception tracebacks.

### `occurred_at`

- Django type: `DateTimeField`
- Required
- Supplied explicitly by the application

### `created_at`

- Django type: `DateTimeField`
- `auto_now_add=True`

### `batch_id`

- Django type: `UUIDField`
- `null=True`
- `blank=True`

### `correlation_id`

- Django type: `UUIDField`
- Required

Every event must belong to one logical notification lifecycle.

### `delivery_attempt_id`

- Django type: `UUIDField`
- `null=True`
- `blank=True`

It becomes mandatory for:

- `delivery_attempted`
- `delivery_succeeded`
- `delivery_failed`

### `idempotency_key`

- Django type: `CharField`
- `max_length=128`
- `unique=True`

This is the database-enforced replay boundary.

### `notification_fingerprint`

- Django type: `CharField`
- `max_length=64`
- Required

It must remain compatible with the stable fingerprint semantics preserved by
v224.

### `rollback_of`

- Django type: self-referencing `ForeignKey`
- `null=True`
- `blank=True`
- `on_delete=models.PROTECT`
- `related_name="rollback_events"`

It is mandatory for:

- `rollback_previewed`
- `rollback_applied`

### `actor_type`

- Django type: `CharField`
- `max_length=32`
- Choices: `ActorType.choices`

Required values:

- `system`
- `scheduler`
- `operator`
- `management_command`
- `test_backend`

### `actor_identifier`

- Django type: `CharField`
- `max_length=128`
- `blank=True`

It must contain a stable non-secret identifier.

### `source`

- Django type: `CharField`
- `max_length=128`
- Required

### Timestamp transition snapshots

The following fields use `DateTimeField(null=True, blank=True)`:

- `checked_at_before`
- `checked_at_after`
- `sent_at_before`
- `sent_at_after`

They document state transitions. Creating an audit event must not itself mutate
the `SavedSearch` timestamps.

### `metadata`

- Django type: `JSONField`
- `default=dict`
- `blank=True`

Metadata must be validated before persistence.

## Model metadata contract

Required database table:

`listings_savedsearchnotificationauditevent`

Required default ordering:

1. `-occurred_at`
2. `-created_at`

Required `get_latest_by`:

`occurred_at`

The model must not define a general-purpose `updated_at` field.

## Index contract

The model must declare these indexes:

| Name | Fields |
|---|---|
| `ssna_saved_occ_idx` | `saved_search`, `occurred_at` |
| `ssna_event_occ_idx` | `event_type`, `occurred_at` |
| `ssna_outcome_occ_idx` | `outcome`, `occurred_at` |
| `ssna_batch_idx` | `batch_id` |
| `ssna_corr_idx` | `correlation_id` |
| `ssna_attempt_idx` | `delivery_attempt_id` |
| `ssna_fingerprint_idx` | `notification_fingerprint` |
| `ssna_rollback_idx` | `rollback_of` |

`idempotency_key` is protected by its unique field constraint and does not need
a duplicate explicit index.

## Check-constraint contract

### `ssna_rollback_link_required`

An event with type `rollback_previewed` or `rollback_applied` must have a
non-null `rollback_of`.

### `ssna_delivery_attempt_required`

An event with type `delivery_attempted`, `delivery_succeeded`, or
`delivery_failed` must have a non-null `delivery_attempt_id`.

## Append-only model contract

The implementation must prevent ordinary application mutation through all
supported model paths.

Required behavior:

- Initial model insertion is allowed.
- Calling `save()` on an existing event raises a clear domain validation error.
- Calling `delete()` raises a clear domain validation error.
- The model’s custom queryset rejects `update()`.
- The model’s custom queryset rejects `delete()`.
- `bulk_update()` is unavailable or explicitly rejected.
- Existing event rows are never rewritten.
- Corrections create new compensating events.
- Rollbacks create new linked rollback events.
- The model is not registered in normal editable Django admin during v229.

The custom manager may retain safe read and create operations.

The append-only guards do not authorize delivery or timestamp changes.

## Persistence write-service contract

Required module:

`listings.saved_search_notification_audit_persistence`

Required function:

`record_saved_search_notification_audit_event`

Required result type:

`SavedSearchNotificationAuditWriteResult`

Required conflict exception:

`SavedSearchNotificationAuditIdempotencyConflict`

The result must expose:

- `event`
- `created`

### Service behavior

The write service must:

1. Validate the event type.
2. Validate the normalized outcome.
3. Validate the actor type.
4. Require `correlation_id`.
5. Require rollback linkage for rollback events.
6. Require delivery-attempt linkage for delivery events.
7. Validate metadata against an allow-list and deny-list.
8. Enter `transaction.atomic()`.
9. Resolve the event by `idempotency_key`.
10. Create the event when no matching key exists.
11. Return the existing event with `created=False` when the replay payload is
    identical.
12. Raise `SavedSearchNotificationAuditIdempotencyConflict` when the same key
    is reused with a different immutable payload.
13. Never deliver email.
14. Never invoke the sender.
15. Never update `last_notification_checked_at`.
16. Never update `last_notification_sent_at`.
17. Never perform scheduler integration.
18. Never perform rollback integration.

Scheduler, delivery, rollback, and operator interfaces must integrate through
later checkpoints.

## Idempotent replay comparison

An existing event replay is identical only when all immutable persisted fields
match after canonical normalization.

The comparison includes:

- Saved-search identity.
- Owner identifier snapshot.
- Event type.
- Outcome.
- Reason code.
- Occurrence time.
- Batch identifier.
- Correlation identifier.
- Delivery-attempt identifier.
- Notification fingerprint.
- Rollback linkage.
- Actor type.
- Actor identifier.
- Source.
- Timestamp transition snapshots.
- Metadata.

`created_at` is excluded because it is generated by the database insertion.

A mismatch must never silently return the old event.

## Metadata privacy contract

Metadata keys must be allow-listed by the implementation.

The following key names or equivalent normalized forms must be rejected:

- `password`
- `secret`
- `api_key`
- `authorization`
- `cookie`
- `session`
- `token`
- `smtp_password`
- `email_body`
- `html_body`
- `plain_text_body`
- `traceback`

The write service must also reject:

- Rendered plain-text email content.
- Rendered HTML email content.
- Credentials.
- API keys.
- SMTP secrets.
- Session identifiers.
- Authorization headers.
- Raw exception tracebacks.
- Arbitrary request payloads.

Metadata validation failure must occur before model insertion.

## Migration contract

Migration `0016_savedsearchnotificationauditevent` must:

- Depend only on `listings.0015_savedsearch_notifications` within the listings
  app.
- Create exactly one model.
- Create no initial data.
- Run no audit backfill.
- Add no scheduler or delivery behavior.
- Add no settings.
- Add no secrets.
- Add the unique idempotency constraint.
- Add all planned indexes.
- Add both planned check constraints.
- Leave existing `SavedSearch` rows unchanged.
- Be reversible while no protected audit references prevent reversal.

A historical backfill requires a separate explicitly designed checkpoint.

## Required v229 tests

The model and migration implementation must include focused tests for:

### Model shape

- Exact fields and field options.
- Choices.
- Table name.
- Ordering.
- Indexes.
- Constraints.
- Related names.
- Protected foreign keys.

### Append-only behavior

- Initial create succeeds.
- Instance update fails.
- Instance delete fails.
- Queryset update fails.
- Queryset delete fails.
- Bulk update fails.
- Compensating event creation succeeds.

### Idempotency

- First write returns `created=True`.
- Identical replay returns the same event with `created=False`.
- Mismatched replay raises the conflict exception.
- Concurrent or repeated logical writes cannot create duplicate idempotency
  keys.

### Event validation

- Rollback events require `rollback_of`.
- Delivery events require `delivery_attempt_id`.
- Invalid event types fail.
- Invalid outcomes fail.
- Invalid actor types fail.

### Privacy

- Allowed metadata persists.
- Every denied key is rejected.
- Nested denied keys are rejected.
- Metadata validation happens before insertion.
- Rendered email bodies are rejected.

### Safety

- No email is delivered.
- No sender is invoked.
- No scheduler integration is introduced.
- No rollback execution is introduced.
- No `SavedSearch` timestamp is mutated.
- Existing v223–v228 checks remain green.
- Full regression remains green.

## Exact implementation acceptance wording

- model save rejects updates
- get or create by `idempotency_key`

## Explicit v228 exclusions

v228:

- Does not create `SavedSearchNotificationAuditEvent`.
- Does not add migration `0016`.
- Does not create the persistence module.
- Does not write audit events.
- Does not change `SavedSearch`.
- Does not change admin behavior.
- Does not register an audit-event admin.
- Does not deliver email.
- Does not add delivery actions.
- Does not add scheduler integration.
- Does not add background processing.
- Does not add retry execution.
- Does not add rollback execution.
- Does not mutate notification timestamps.
- Does not change templates.
- Does not change settings or secrets.
- Does not create `backend/docs`.

Only the v228 test and v228 root contract document should be staged.

## Acceptance criteria

- Exact model fields are contractually fixed.
- Exact migration name and dependency are fixed.
- Exact event, outcome, and actor choices are fixed.
- Exact indexes are fixed.
- Check constraints are fixed.
- Append-only model behavior is fixed.
- Persistence write-service behavior is fixed.
- Replay-safe idempotency behavior is fixed.
- Metadata privacy validation is fixed.
- No runtime or migration implementation is included.
- Full regression remains green.

## Next checkpoint

v229: saved-search notification audit persistence model and migration
implementation
