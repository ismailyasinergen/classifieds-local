# v256 — Saved-Search Notification Production Delivery Pilot Execution Authorization Contract

## Checkpoint identity

- Base:
  `project-checkpoint-v255-saved-search-notification-production-delivery-pilot-readiness-closeout-audit`
- Target:
  `project-checkpoint-v256-saved-search-notification-production-delivery-pilot-execution-authorization-contract`
- Marker:
  `V256_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_EXECUTION_AUTHORIZATION_CONTRACT`

## Purpose

v256 defines the contract for issuing one tightly bounded authorization for a
single saved-search notification production pilot invocation.

This checkpoint performs no production delivery.

The contract is documentation and test only.

## Exact v256 scope

v256 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_execution_authorization_contract_v256.py`
2. `docs/saved_search_notification_production_delivery_pilot_execution_authorization_contract_v256.md`

## Proposed v257 implementation scope

v257 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_execution_authorization_v257.py`
2. `docs/saved_search_notification_production_delivery_pilot_execution_authorization_v257.md`

v257 remains documentation and test only.

It must not modify production runtime or execute production delivery.

## Authorization objective

An authorization binds one approved operator action to:

- One positive owner identifier
- One approved limit between one and three
- One matching preview
- One fresh readiness result
- One command fingerprint
- Two distinct reviewer approvals
- One short execution window
- At most one production invocation

Authorization is not a reusable credential.

## Authorization limit boundary

The pilot authorization limit remains exactly:

- Minimum: 1
- Maximum: 3

The underlying production batch cap remains 25.

The authorization lane must not expand the pilot above three.

## Freshness windows

The contract defines:

- Readiness evidence maximum age: 300 seconds
- Preview evidence maximum age: 300 seconds
- Authorization lifetime: 600 seconds

Evidence older than its maximum age is stale.

An authorization with a lifetime above 600 seconds is invalid.

Expired authorization cannot be renewed automatically.

## Authorization stage order

The deterministic order is:

1. Collect immutable bindings.
2. Verify fresh readiness.
3. Verify fresh matching preview.
4. Verify provider and sender state.
5. Verify reviewer approvals.
6. Issue one-shot authorization.
7. Consume or terminate authorization.
8. Perform mandatory post-run review.

No stage may be skipped.

## Required authorization fields

The authorization record requires:

- `authorization_id`
- `change_record_id`
- `pilot_owner_id`
- `approved_limit`
- `preview_owner_id`
- `preview_limit`
- `preview_candidate_count`
- `readiness_status`
- `readiness_checked_at_utc`
- `preview_checked_at_utc`
- `issued_at_utc`
- `expires_at_utc`
- `operator_identity`
- `primary_reviewer_identity`
- `secondary_reviewer_identity`
- `provider_status`
- `sender_verification_status`
- `feature_gate_verified`
- `backend_policy_verified`
- `rollback_reviewer_identity`
- `command_fingerprint`
- `authorization_state`
- `consumed_at_utc`
- `incident_reference`

## Immutable bindings

After authorization, these fields cannot change:

- Authorization identifier
- Change-record identifier
- Pilot owner identifier
- Approved limit
- Preview owner identifier
- Preview limit
- Preview candidate count
- Operator identity
- Primary reviewer identity
- Secondary reviewer identity
- Command fingerprint
- Issue timestamp
- Expiration timestamp

Changing any immutable binding invalidates authorization.

## Authorization lifecycle

Allowed states are:

1. `draft`
2. `ready_for_review`
3. `authorized`
4. `consumed`
5. `expired`
6. `revoked`
7. `failed_closed`

Terminal states are:

- `consumed`
- `expired`
- `revoked`
- `failed_closed`

A terminal authorization cannot return to `authorized`.

## One-shot consumption

An authorization permits exactly one production invocation.

The authorization must become `consumed` before a second invocation can occur.

Reuse after consumption is prohibited.

Failure to establish one-shot consumption produces fail-closed behavior.

## Owner and limit binding

The authorization owner must equal:

- The approved owner
- The preview owner
- The production-command owner

The authorization limit must equal:

- The approved limit
- The preview limit
- The production-command limit

Any mismatch invalidates authorization.

## Pilot preview boundary

The nonproduction preview remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

The preview:

- Contains no production confirmation flags.
- Targets exactly one owner.
- Uses a limit between one and three.
- Returns at least one candidate.
- Does not exceed the approved limit.
- Produces understood classifications.
- Produces zero unexpected refusals.

A fresh preview is required after any owner or limit change.

## Strict readiness boundary

The strict-readiness command remains:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

Authorization requires:

- Status `ready`
- All nine readiness checks
- Evidence no older than 300 seconds
- No active incident
- No command-surface mismatch

## Sanitized readiness evidence

The JSON command remains:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

Retain only:

- Overall readiness status
- Stable check identifiers
- Stable reason codes
- Ready count
- Not-ready count
- Warning count
- Readiness timestamp

Raw configuration values remain excluded.

## Provider and sender verification

Authorization requires current evidence that:

- The feature gate is enabled.
- The approved email backend is configured.
- The default sender is configured.
- Sender identity or domain is verified.
- Provider credentials are available outside retained evidence.
- The provider quota covers the approved limit.
- Provider status is operational.
- Bounce and complaint ownership is assigned.

Provider or sender degradation revokes authorization.

## Reviewer approval boundary

Two explicit and distinct reviewer approvals are required:

- Primary reviewer
- Secondary reviewer

The operator cannot silently substitute either reviewer.

Reviewer identity collision invalidates authorization.

Both approvals must apply to the same owner, limit, preview and command
fingerprint.

## Command fingerprint

The command fingerprint binds:

- Command name
- `--execute-production-send`
- `--confirm-production-delivery`
- Owner identifier
- Limit

The reviewed production pattern remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

A fingerprint mismatch invalidates authorization.

v256 does not execute this command.

## Authorization preconditions

Authorization requires:

- The v255 pilot-readiness lane is closed.
- One positive owner identifier is approved.
- The pilot limit is between one and three.
- Preview owner matches approved owner.
- Preview limit matches approved limit.
- Preview candidate count is valid.
- Strict readiness is fresh and ready.
- All nine readiness checks are present.
- Preview evidence is fresh.
- Authorization lifetime is valid.
- Feature gate remains enabled.
- Backend and sender state remain approved.
- Provider credentials remain available.
- The provider quota covers the approved limit.
- Provider status remains operational.
- No concurrent owner-scoped run exists.
- No unresolved incident exists.
- Rollback reviewer remains available.
- Two distinct reviewers approve.
- Operator and reviewer identities are recorded.
- Command fingerprint matches owner and limit.
- Both production confirmation flags remain present.

## Stop reasons

Authorization fails closed for:

- `pilot_readiness_lane_not_closed`
- `invalid_owner_id`
- `invalid_pilot_limit`
- `preview_owner_mismatch`
- `preview_limit_mismatch`
- `preview_candidate_count_invalid`
- `readiness_not_ready`
- `readiness_check_count_mismatch`
- `readiness_evidence_stale`
- `preview_evidence_stale`
- `authorization_ttl_invalid`
- `authorization_expired`
- `authorization_already_consumed`
- `authorization_revoked`
- `authorization_failed_closed`
- `feature_gate_disabled`
- `email_backend_rejected`
- `default_sender_missing`
- `sender_unverified`
- `provider_credentials_unavailable`
- `provider_quota_insufficient`
- `provider_not_operational`
- `concurrent_owner_run`
- `unresolved_incident`
- `rollback_reviewer_missing`
- `primary_reviewer_missing`
- `secondary_reviewer_missing`
- `reviewer_identity_collision`
- `operator_identity_missing`
- `command_fingerprint_mismatch`
- `production_confirmation_missing`

Any stop reason blocks execution.

## Authorization evidence package

Retain:

- Authorization and change-record identifiers
- Pilot owner identifier
- Approved limit
- Preview candidate count
- Readiness status and counts
- Readiness timestamp
- Preview timestamp
- Issue and expiration timestamps
- Operator identity
- Primary reviewer identity
- Secondary reviewer identity
- Provider status
- Sender-verification status
- Feature-gate verification
- Backend-policy verification
- Rollback-reviewer identity
- Command fingerprint
- Authorization state
- Consumption timestamp
- Decision
- Stable reason codes
- Incident reference

## Privacy and secret boundary

Never retain:

- SMTP password
- Confidential SMTP username
- API key
- Access token
- Recipient email address
- Default sender value
- Raw backend path
- Saved-search name
- Saved-search querystring
- Rendered email subject
- Rendered email body
- Provider response body
- Raw exception traceback

Suspected exposure invalidates authorization.

## Revocation boundary

Authorization must be revoked when:

- Provider status degrades.
- Sender verification changes.
- Feature gate changes.
- Owner approval changes.
- Reviewer approval changes.
- Preview becomes stale.
- Readiness becomes stale.
- Owner or limit changes.
- Command fingerprint changes.
- A concurrent run appears.
- An incident opens.
- Rollback reviewer becomes unavailable.

Revoked authorization cannot be reused.

## Post-run review boundary

Every consumed authorization requires immediate post-run review of:

- Delivered count
- Skipped count
- Refused count
- Failed count
- `delivery_attempted`
- `delivery_succeeded`
- `delivery_failed`
- `sent_timestamp_recorded`
- Sent-timestamp consistency
- Duplicate-attempt status
- Audit gaps
- Provider anomalies
- Incident state

Authorization does not imply post-run success.

## Prohibited actions

The authorization contract prohibits:

- Production delivery during the contract checkpoint
- Authorization without a positive owner identifier
- Authorization without an explicit pilot limit
- Limit below one
- Limit above three
- Stale readiness evidence
- Stale preview evidence
- Authorization longer than 600 seconds
- Missing reviewer approval
- Identical reviewer identities
- Owner change after authorization
- Limit change after authorization
- Command-fingerprint change after authorization
- Authorization reuse
- Execution after expiration
- Execution after revocation
- Global all-owner execution
- Multi-owner execution
- Readiness bypass
- Preview bypass
- Production-confirmation bypass
- Provider-verification bypass
- Blind retry
- Automatic authorization renewal
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

## Runtime and schema boundary

v256 and the proposed v257 implementation introduce no changes to:

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

## Acceptance gate

v257 is accepted only when:

- Its scope is exactly the two contracted files.
- Authorization evaluation is deterministic.
- Owner and limit bindings are immutable.
- Freshness windows are enforced.
- Authorization lifetime is enforced.
- Two distinct reviewer approvals are enforced.
- Command fingerprint is enforced.
- Authorization is one-shot.
- Terminal states cannot be reopened.
- Stop reasons are stable.
- Evidence is sanitized.
- No production delivery is executed.
- Runtime, scheduler, schema and UI remain unchanged.
- Focused and historical tests pass.
- Full regression remains green.

## Next checkpoint

v257: saved-search notification production delivery pilot execution authorization implementation
