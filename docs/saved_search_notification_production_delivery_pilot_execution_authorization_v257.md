# v257 — Saved-Search Notification Production Delivery Pilot Execution Authorization

## Checkpoint identity

- Base:
  `project-checkpoint-v256-saved-search-notification-production-delivery-pilot-execution-authorization-contract`
- Target:
  `project-checkpoint-v257-saved-search-notification-production-delivery-pilot-execution-authorization`
- Marker:
  `V257_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_EXECUTION_AUTHORIZATION`

## Purpose

v257 implements the v256 pilot-execution authorization contract as a
deterministic documentation-and-test-only reference implementation.

The implementation provides:

- Canonical SHA-256 command fingerprints
- Deterministic authorization evaluation
- Stable ordered stop reasons
- Immutable-binding snapshots
- Deterministic lifecycle transitions
- One-shot consumption
- Strict evidence sanitization
- Fail-closed terminal-state handling

This checkpoint performs no production delivery.

## Exact v257 scope

v257 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_execution_authorization_v257.py`
2. `docs/saved_search_notification_production_delivery_pilot_execution_authorization_v257.md`

## Proposed v258 closeout scope

v258 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_execution_authorization_closeout_audit_v258.py`
2. `docs/saved_search_notification_production_delivery_pilot_execution_authorization_closeout_audit_v258.md`

v258 remains documentation and test only.

## Implementation boundary

The reference implementation exists only in the v257 test module and this
document.

It does not modify:

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
- Database migrations

No reference function opens an email connection or invokes a production
command.

## Authorization limit

The implementation enforces:

- Minimum approved limit: 1
- Maximum approved limit: 3

The underlying production batch cap remains 25.

The authorization evaluator rejects limits below one or above three.

## Freshness and lifetime windows

The evaluator enforces:

- Readiness evidence maximum age: 300 seconds
- Preview evidence maximum age: 300 seconds
- Authorization lifetime maximum: 600 seconds

The exact 300-second freshness boundary is accepted.

Evidence older than 300 seconds is rejected.

An authorization lifetime greater than 600 seconds is rejected.

An authorization is expired when the evaluation time reaches or exceeds its
expiration timestamp.

## Canonical command fingerprint

The command fingerprint is the SHA-256 digest of canonical JSON containing:

- `command_name`
- `execute_production_send`
- `confirm_production_delivery`
- `owner_id`
- `limit`

Canonical JSON uses sorted keys and compact separators.

Changing any fingerprint field changes the digest.

The fingerprint therefore binds:

- The command identity
- Both production confirmation flags
- The owner identifier
- The approved limit

## Authorization evidence model

The reference evidence includes:

- Authorization identifier
- Change-record identifier
- Pilot-readiness closeout state
- Approved owner
- Approved limit
- Preview owner
- Preview limit
- Preview candidate count
- Readiness state and check count
- Readiness timestamp
- Preview timestamp
- Issue and expiration timestamps
- Feature-gate state
- Backend-policy state
- Default-sender state
- Sender-verification state
- Provider credential availability
- Provider quota
- Provider operational state
- Concurrent-run state
- Incident state
- Rollback-reviewer state
- Operator identity
- Primary reviewer identity
- Secondary reviewer identity
- Command fields
- Command fingerprint
- Authorization lifecycle state
- Consumption timestamp

## Deterministic authorization evaluation

A successful result contains only:

- `authorized`
- `status`
- `reason_codes`
- `authorization_id`
- `pilot_owner_id`
- `approved_limit`
- `preview_candidate_count`
- `command_fingerprint`
- `expires_at_utc`

The evaluator returns `authorized` only when every gate passes.

Any stop reason returns `not_authorized`.

Reason codes remain ordered according to the v256 contract.

## Owner and preview matching

Authorization requires:

- A positive owner identifier
- Preview owner equal to approved owner
- Preview limit equal to approved limit
- Preview candidate count between one and the approved limit
- Production command owner equal to approved owner
- Production command limit equal to approved limit

A mismatch fails closed.

## Strict readiness requirements

Authorization requires:

- Readiness status `ready`
- All nine readiness checks
- Readiness evidence no older than 300 seconds

The strict-readiness command remains:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

The JSON report remains:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

The reference implementation does not execute either command during production
delivery.

## Provider and sender requirements

Authorization requires:

- Enabled production feature gate
- Approved email backend
- Configured default sender
- Verified sender identity or domain
- Available provider credentials
- Provider quota covering the approved limit
- Operational provider state
- No concurrent owner-scoped run
- No unresolved incident
- Available rollback reviewer

Failure of any requirement blocks authorization.

## Reviewer and operator requirements

Authorization requires:

- Nonempty operator identity
- Nonempty primary reviewer identity
- Nonempty secondary reviewer identity
- Distinct primary and secondary reviewer identities

A reviewer identity collision fails closed.

## Stable stop reasons

The evaluator retains all 31 contract stop reasons:

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

The implementation verifies that every reason is reachable.

## Immutable-binding snapshot

The immutable snapshot retains:

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

The snapshot order is deterministic.

Changing an immutable field requires a new authorization.

## Lifecycle transitions

The supported progression is:

1. `draft`
2. `ready_for_review`
3. `authorized`
4. `consumed`

Alternative terminal transitions are:

- `expired`
- `revoked`
- `failed_closed`

The reference transition actions are:

- `submit`
- `authorize`
- `consume`
- `expire`
- `revoke`
- `fail_closed`

An invalid transition becomes `failed_closed`.

## Terminal-state locking

Terminal states are:

- `consumed`
- `expired`
- `revoked`
- `failed_closed`

A terminal state cannot transition back to `authorized`.

Attempts to reopen a terminal state return `terminal_state_locked`.

## One-shot consumption

The consumption helper:

1. Compares the presented fingerprint with the authorized fingerprint.
2. Re-evaluates all authorization gates.
3. Requires the lifecycle state `authorized`.
4. Transitions exactly once to `consumed`.
5. Records the consumption timestamp in its sanitized result.

A second consumption attempt fails with
`authorization_already_consumed`.

The helper does not invoke the production sender.

## Preview and production command boundary

The reviewed nonproduction preview remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

The reviewed production command remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

v257 executes neither command.

Both production confirmations remain part of the fingerprint.

## Evidence allowlist

The sanitizer retains only approved fields from the v256 evidence contract,
including:

- Authorization and change-record identifiers
- Owner and limit
- Preview candidate count
- Readiness status and counts
- Readiness and preview timestamps
- Issue and expiration timestamps
- Operator and reviewer identities
- Provider and sender states
- Feature-gate and backend-policy verification
- Rollback reviewer
- Command fingerprint
- Authorization state
- Consumption timestamp
- Decision
- Stable reason codes
- Incident reference

Unknown fields are discarded.

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

## Post-consumption review boundary

Consumption does not mean pilot success.

Any future authorized execution still requires immediate reconciliation of:

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

## Prohibited actions

The implementation continues to prohibit:

- Production delivery during this checkpoint
- Authorization without a positive owner
- Authorization without an explicit limit
- Limit below one
- Limit above three
- Stale readiness evidence
- Stale preview evidence
- Authorization lifetime above 600 seconds
- Authorization without two distinct reviewers
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

v257 introduces no changes to runtime, scheduler, schema or UI.

The latest listings migration remains:

`0016_savedsearchnotificationauditevent`

Migration `0017` remains absent.

## Completion gate

v257 is complete only when:

- Commit scope is exactly two files.
- v256 remains unchanged.
- Fingerprints are deterministic.
- Every fingerprint field is bound.
- Freshness and lifetime windows are enforced.
- Every stop reason is reachable.
- Reason-code ordering is deterministic.
- Immutable snapshots are stable.
- Lifecycle transitions are deterministic.
- Terminal states cannot reopen.
- Consumption succeeds exactly once.
- Authorization reuse fails closed.
- Evidence sanitization is allowlist based.
- Sensitive fields are excluded.
- No production delivery occurs.
- Focused tests pass.
- Historical safety tests pass.
- Full regression passes.
- Working tree is clean.
- The v257 tag resolves to final HEAD.

## Next checkpoint

v258: saved-search notification production delivery pilot execution authorization closeout audit
