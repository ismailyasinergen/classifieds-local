# v254 — Saved-Search Notification Production Delivery Pilot Readiness

## Checkpoint identity

- Base:
  `project-checkpoint-v253-saved-search-notification-production-delivery-pilot-readiness-contract`
- Target:
  `project-checkpoint-v254-saved-search-notification-production-delivery-pilot-readiness`
- Marker:
  `V254_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_READINESS`

## Purpose

v254 implements the v253 pilot-readiness contract as a deterministic,
documentation-and-test-only reference workflow.

The implementation provides:

- Ordered readiness stages
- Stable preflight reason codes
- Stable post-run reason codes
- A strict evidence allowlist
- Owner and limit matching rules
- Deterministic go or no-go results
- Deterministic post-run success or failure results

This checkpoint performs no production delivery.

## Exact v254 scope

v254 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_readiness_v254.py`
2. `docs/saved_search_notification_production_delivery_pilot_readiness_v254.md`

## Proposed v255 closeout scope

v255 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_readiness_closeout_audit_v255.py`
2. `docs/saved_search_notification_production_delivery_pilot_readiness_closeout_audit_v255.md`

v255 remains documentation and test only.

## Implementation boundary

The v254 implementation exists only in the v254 test module and this document.

It does not modify:

- Settings
- Delivery sender
- Delivery command
- Readiness service
- Readiness command
- Scheduler
- Audit runtime
- Audit persistence
- Models
- Admin
- URLs
- Templates
- Browser UI
- Migrations

The reference evaluators do not call an email backend and do not execute a
production command.

## Pilot limit boundary

The approved pilot limit remains exactly:

- Minimum: 1
- Maximum: 3

The evaluator rejects:

- Limits below one
- Limits above three
- Preview candidate counts below one
- Preview candidate counts above the approved limit

The underlying production batch maximum remains 25, but pilot authorization
remains narrowed to a maximum of three.

## Decision-stage order

The implementation evaluates readiness in this order:

1. Authorization
2. Owner eligibility
3. Environment verification
4. Strict readiness
5. Matching preview
6. Reviewer go decision
7. Guarded production invocation
8. Post-run verification

The order is deterministic and audit-friendly.

## Preflight evidence model

The reference preflight evidence includes:

- Positive owner identifier
- Approved pilot limit
- Owner approval
- Reviewer approval
- Owner-scope isolation
- Notification opt-in state
- Eligible due saved-search count
- Usable recipient state
- Concurrent owner-run state
- Unresolved incident state
- Feature-gate state
- Email-backend policy state
- Default-sender configuration state
- Sender-verification state
- Provider-credential availability
- Provider quota
- Provider operational state
- Bounce and complaint review ownership
- Approved execution window
- Rollback-reviewer availability
- Strict-readiness state
- Readiness-check count
- Sanitized readiness JSON retention
- Deployed command-help review
- Source-verified rollback controls
- Preview owner
- Preview limit
- Preview candidate count
- Preview skip-classification review
- Preview unexpected-refusal count

No raw credential, recipient or message payload belongs in this model.

## Preflight decision result

The preflight evaluator returns only:

- `ready`
- `status`
- `reason_codes`
- `owner_id`
- `approved_limit`
- `preview_candidate_count`

The result excludes:

- SMTP credentials
- API credentials
- Recipient addresses
- Sender values
- Backend paths
- Saved-search payloads
- Rendered email content
- Provider response bodies
- Raw exception traces

## Stable preflight reason codes

The implementation may return these ordered reason codes:

- `invalid_owner_id`
- `invalid_pilot_limit`
- `owner_not_approved`
- `reviewer_not_approved`
- `owner_scope_not_isolated`
- `notification_opt_in_disabled`
- `no_eligible_due_saved_search`
- `recipient_unusable`
- `concurrent_owner_run`
- `unresolved_incident`
- `feature_gate_disabled`
- `email_backend_rejected`
- `default_sender_missing`
- `sender_unverified`
- `provider_credentials_unavailable`
- `provider_quota_insufficient`
- `provider_not_operational`
- `bounce_complaint_owner_missing`
- `execution_window_not_approved`
- `rollback_reviewer_missing`
- `strict_readiness_not_ready`
- `readiness_check_count_mismatch`
- `readiness_json_missing`
- `deployed_help_not_reviewed`
- `rollback_controls_unverified`
- `preview_owner_mismatch`
- `preview_limit_mismatch`
- `preview_candidate_count_invalid`
- `preview_skips_unresolved`
- `preview_unexpected_refusal`

Any returned reason code means no-go.

## Strict readiness verification

The operator-facing strict-readiness command remains:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

All nine readiness checks must remain present.

The default local development configuration is expected to report `not_ready`
because the production-delivery feature gate is disabled.

A production-like reviewed configuration must report `ready`.

## Sanitized readiness evidence

The operator-facing JSON command remains:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

Retain only:

- Overall readiness status
- Stable check identifiers
- Stable reason codes
- Ready count
- Not-ready count
- Warning count

Do not retain raw configuration values.

## Deployed command verification

Inspect deployed help before preview:

    docker compose exec -T web python manage.py process_saved_search_notifications --help

Verify these controls remain present:

- `--execute-production-send`
- `--confirm-production-delivery`
- `--owner-id`
- `--limit`

A deployed-help mismatch produces no-go.

## Matching pilot preview

The preview pattern remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

The preview:

- Uses one positive approved owner
- Uses the approved limit
- Contains no production confirmation flags
- Must return at least one candidate
- Must not exceed the approved limit
- Must have understood skip classifications
- Must have zero unexpected refusals

The reference evaluator returns no-go for an owner mismatch, limit mismatch,
invalid candidate count, unresolved skip classification or unexpected refusal.

## Reviewer go decision

The evaluator can report ready only when:

- Owner approval is present.
- Reviewer approval is present.
- Owner scope is isolated.
- No concurrent owner run is detected.
- No incident is open.
- Provider status is operational.
- Provider quota covers the approved limit.
- Strict readiness reports ready.
- All nine readiness checks are present.
- Sanitized readiness JSON is retained.
- Deployed command help was reviewed.
- Rollback controls were source verified.
- Preview owner and limit match approval.
- Preview candidate count is valid.
- Preview classifications are understood.
- Preview unexpected-refusal count is zero.

A ready result does not execute delivery.

## Guarded production command boundary

The reviewed production pattern remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

The v254 tests and script do not execute this command.

Any later authorized invocation must use:

- Both production confirmation flags
- The same owner used in preview
- The same limit used in preview
- A limit between one and three

## Evidence allowlist

The sanitizer retains only approved operational fields, including:

- Change-record identifier
- Pilot owner identifier
- Approved limit
- Operator and reviewer identities
- Execution window
- UTC start and finish times
- Feature-gate verification
- Backend-policy verification
- Sender-verification status
- Provider status
- Provider-quota verification
- Readiness counts
- Preview counts
- Production counts
- Audit verification
- Sent-timestamp verification
- Duplicate-attempt verification
- Rollback-readiness verification
- Decision
- Incident reference

Unrecognized fields are discarded.

## Sensitive evidence exclusions

The sanitizer excludes:

- SMTP password
- Confidential SMTP username
- API key
- Access token
- Recipient email address
- Default sender value
- Raw email-backend path
- Saved-search name
- Saved-search querystring
- Rendered email subject
- Rendered email body
- Provider response body
- Raw exception traceback

## Post-run evidence model

The reference post-run evidence includes:

- Preview candidate count
- Delivered count
- Skipped count
- Refused count
- Failed count
- `delivery_attempted` event count
- `delivery_succeeded` event count
- `delivery_failed` event count
- `sent_timestamp_recorded` event count
- Sent-timestamp consistency
- Duplicate-attempt review state
- Audit-gap review state
- Provider-anomaly state
- Incident state

## Post-run reconciliation

The implementation verifies:

- Failed count equals zero.
- Unexpected refusal count equals zero.
- Delivered, skipped, refused and failed counts reconcile to preview candidates.
- `delivery_attempted` count equals delivered plus failed.
- `delivery_succeeded` count equals delivered.
- `delivery_failed` count equals failed.
- `sent_timestamp_recorded` count equals delivered.
- Sent-timestamp evidence is consistent.
- Duplicate-attempt review is clean.
- No audit gap exists.
- No provider anomaly exists.
- No incident remains open.

Understood skipped items may coexist with a successful pilot when all counts
reconcile.

## Stable post-run reason codes

The implementation may return:

- `failed_count_nonzero`
- `unexpected_refusal_count_nonzero`
- `delivery_counts_unreconciled`
- `attempted_event_count_mismatch`
- `success_event_count_mismatch`
- `failure_event_count_mismatch`
- `timestamp_event_count_mismatch`
- `sent_timestamp_inconsistent`
- `duplicate_attempt_anomaly`
- `audit_gap_detected`
- `provider_anomaly`
- `incident_open`

Any returned reason code means the pilot is not successful.

## Persistent audit verification

The read-only interface remains:

    /staff/saved-search-notification-audit/

For each successful item verify:

1. `delivery_attempted`
2. `delivery_succeeded`
3. `sent_timestamp_recorded`

For each failed item verify:

1. `delivery_attempted`
2. `delivery_failed`

Audit rows remain append-only and must not be edited or deleted.

## Rollback readiness

Before an authorized pilot, verify:

- Deployed command help
- Source-supported rollback controls
- Rollback reviewer
- Existing rollback preview workflow
- Owner and attempt selection
- Post-rollback audit verification
- Restored timestamp verification
- Unrelated timestamp preservation

Never invent rollback flags.

Never use direct SQL or Django shell timestamp repair.

## No-go conditions

A no-go result is mandatory for:

- Invalid owner identifier
- Invalid pilot limit
- Missing owner approval
- Missing reviewer approval
- Nonisolated owner scope
- Disabled notification opt-in
- No eligible due saved search
- Unusable recipient state
- Concurrent owner run
- Open incident
- Disabled feature gate
- Rejected email backend
- Missing default sender
- Unverified sender identity or domain
- Missing provider credentials
- Insufficient provider quota
- Nonoperational provider
- Missing bounce or complaint owner
- Unapproved execution window
- Missing rollback reviewer
- Strict readiness failure
- Missing readiness check
- Missing sanitized readiness JSON
- Unreviewed deployed help
- Unverified rollback controls
- Preview owner mismatch
- Preview limit mismatch
- Invalid preview candidate count
- Unresolved preview classification
- Unexpected preview refusal

## Prohibited actions

The implementation continues to prohibit:

- Production execution by tests
- Global all-owner execution
- Multi-owner command execution
- Limit below one
- Limit above three
- Owner change after preview
- Limit change after preview
- Readiness bypass
- Preview bypass
- Production-confirmation bypass
- Provider-verification bypass
- Blind retry
- Automatic phase promotion
- Automatic scheduler enablement
- Celery enablement
- Cron enablement
- Startup-time delivery
- Request-time delivery
- Manual sent-timestamp edits
- Manual audit-event deletion
- Direct SQL repair
- Django shell timestamp repair
- Credential logging
- Recipient-payload logging
- Saved-search-payload logging
- Silent partial-failure handling

## Runtime and schema boundary

v254 introduces no changes to:

- Settings
- Production sender
- Production command
- Readiness service
- Readiness command
- Scheduler
- Matcher
- Renderer
- Audit runtime
- Audit persistence
- Models
- Admin
- URLs
- Templates
- Browser UI
- Background workers
- Database migrations

The latest listings migration remains:

`0016_savedsearchnotificationauditevent`

Migration `0017` remains absent.

## Completion gate

v254 is complete only when:

- Its commit scope is exactly two files.
- v253 remains unchanged.
- The pilot limit remains one through three.
- Preflight evaluation is deterministic.
- Post-run evaluation is deterministic.
- Reason-code order is stable.
- Evidence output is sanitized.
- Sensitive fields are excluded.
- Preview remains nonproduction.
- The production command retains both confirmation flags.
- Tests execute no production delivery.
- Focused tests pass.
- Historical safety tests pass.
- Full regression passes.
- Runtime, scheduler, schema and UI remain unchanged.
- Working tree is clean.
- The v254 tag resolves to final HEAD.

## Next checkpoint

v255: saved-search notification production delivery pilot readiness closeout audit
