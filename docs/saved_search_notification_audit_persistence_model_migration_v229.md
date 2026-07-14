# v229 — Saved-Search Notification Audit Persistence Model and Migration

## Checkpoint identity

- Base checkpoint:
  `project-checkpoint-v228-saved-search-notification-audit-persistence-implementation-contract`
- Target checkpoint:
  `project-checkpoint-v229-saved-search-notification-audit-persistence-model-migration`
- Marker:
  `V229_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_MODEL_MIGRATION`
- Migration:
  `listings.0016_savedsearchnotificationauditevent`

## Purpose

v229 implements the database model and migration defined by the v228
implementation contract.

The checkpoint introduces the append-only persistence structure without
integrating it into notification evaluation, rendering, delivery, scheduling,
rollback execution, or Django admin.

## Implemented runtime model

Model:

`SavedSearchNotificationAuditEvent`

Database table:

`listings_savedsearchnotificationauditevent`

The model stores:

- Saved-search identity.
- Owner identifier snapshot.
- Event taxonomy and normalized outcome.
- Stable idempotency and fingerprint values.
- Batch, correlation, and delivery-attempt identifiers.
- Rollback linkage.
- Actor and source context.
- Notification timestamp transition snapshots.
- Privacy-minimized JSON metadata.
- Event occurrence and insertion timestamps.

## Stable event taxonomy

- `evaluation_started`
- `skipped_notifications_disabled`
- `skipped_missing_recipient`
- `dry_run_rendered`
- `delivery_attempted`
- `delivery_succeeded`
- `delivery_failed`
- `sent_timestamp_recorded`
- `rollback_previewed`
- `rollback_applied`

## Stable outcomes

- `pending`
- `skipped`
- `succeeded`
- `failed`
- `rolled_back`

## Stable actor types

- `system`
- `scheduler`
- `operator`
- `management_command`
- `test_backend`

## Append-only safeguards

The supported model API now prevents ordinary mutation:

- Existing model instances cannot be saved again.
- Instance deletion is rejected.
- QuerySet update is rejected.
- QuerySet deletion is rejected.
- QuerySet bulk update is rejected.
- Creation remains available.
- Corrections must be represented by later compensating events.
- Rollback history must be represented by linked rollback events.

These safeguards protect supported application paths. They do not claim to be
database-trigger-level immutability.

## Protected relationships

`saved_search` uses `PROTECT`.

Once an audit event references a saved search, that saved search cannot be
deleted through Django’s normal deletion collector.

`rollback_of` is a protected self-reference.

Linked rollback history cannot be silently removed through normal deletion.

## Database constraints

### Unique idempotency boundary

`idempotency_key` is unique.

### Rollback linkage

Constraint:

`ssna_rollback_link_required`

The following events require `rollback_of`:

- `rollback_previewed`
- `rollback_applied`

### Delivery-attempt linkage

Constraint:

`ssna_delivery_attempt_required`

The following events require `delivery_attempt_id`:

- `delivery_attempted`
- `delivery_succeeded`
- `delivery_failed`

## Explicit indexes

- `ssna_saved_occ_idx`
- `ssna_event_occ_idx`
- `ssna_outcome_occ_idx`
- `ssna_batch_idx`
- `ssna_corr_idx`
- `ssna_attempt_idx`
- `ssna_fingerprint_idx`
- `ssna_rollback_idx`

## Migration contract

Migration:

`0016_savedsearchnotificationauditevent`

Dependency:

`listings.0015_savedsearch_notifications`

The migration:

- Creates exactly one new model.
- Contains no data migration.
- Performs no historical backfill.
- Adds no scheduler behavior.
- Adds no delivery behavior.
- Adds no settings or credentials.
- Leaves existing `SavedSearch` rows unchanged.
- Creates all v228 indexes and constraints.

## v227 transition

The historical v227 design test originally proved that the future model and
migration did not yet exist.

v229 converts that historical absence assertion into a transition-aware guard:

- Before the v229 test module exists, model and migration absence is required.
- Once v229 is packaged, model and migration presence is required.
- The original v227 design constants and rollout contract remain unchanged.

## v228 transition

The v228 contract test previously asserted that the future model and migration
were absent.

v229 updates that guard so it now:

- Confirms model and migration presence when the v229 test module is packaged.
- Continues to confirm the persistence write-service module is absent.
- Preserves the historical v228 contract definitions.

## Explicit exclusions

v229 does not:

- Create the persistence write service.
- Record audit events from scheduler execution.
- Record audit events from email rendering.
- Record audit events from test-backend delivery.
- Record audit events from rollback execution.
- Add retry or background execution.
- Register the audit model in editable Django admin.
- Persist email bodies.
- Persist credentials, authorization headers, sessions, or secrets.
- Mutate `last_notification_checked_at`.
- Mutate `last_notification_sent_at`.
- Deliver email.
- Change notification templates.
- Change email settings.
- Create `backend/docs`.

## Acceptance gates

- Model shape matches v228.
- Migration dependency is exact.
- Migration creates one model.
- All explicit indexes are present.
- Both check constraints are present.
- Idempotency uniqueness is enforced.
- Initial insert succeeds.
- Supported update and deletion paths fail closed.
- Saved-search deletion is protected after an audit reference exists.
- Valid linked rollback events can be created.
- Invalid rollback and delivery events fail at the database boundary.
- No persistence write-service module exists.
- No editable admin registration exists.
- Notification timestamps remain unchanged.
- Existing saved-search and notification tests remain green.
- Full regression remains green.

## Next checkpoint

v230: saved-search notification audit append-only write service implementation
