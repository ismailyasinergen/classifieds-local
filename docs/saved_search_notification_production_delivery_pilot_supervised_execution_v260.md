# v260 — Saved-Search Notification Production Delivery Pilot Supervised Execution

## Checkpoint identity

- Base:
  `project-checkpoint-v259-saved-search-notification-production-delivery-pilot-supervised-execution-contract`
- Target:
  `project-checkpoint-v260-saved-search-notification-production-delivery-pilot-supervised-execution`
- Marker:
  `V260_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION`

## Purpose

v260 implements the v259 supervised-execution contract as a deterministic,
documentation-and-test-only reference implementation.

The implementation provides:

- Canonical SHA-256 pre-send freeze fingerprinting
- Deterministic preflight evaluation
- All 38 ordered abort reasons
- Immutable execution-binding snapshots
- A bounded nonexecuting production plan
- One-shot authorization consumption
- Deterministic post-run reconciliation
- A strict evidence allowlist

This checkpoint performs no production delivery.

## Exact v260 scope

v260 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_v260.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_v260.md`

## Proposed v261 closeout scope

v261 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_closeout_audit_v261.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_closeout_audit_v261.md`

v261 remains documentation and test only.

## Implementation boundary

All v260 reference functions exist only in the v260 test module.

They do not modify or invoke:

- Production sender
- Production command
- Scheduler
- Matcher
- Renderer
- Readiness runtime
- Audit runtime
- Models
- Admin
- URLs
- Templates
- Migrations

No production command is executed.

## Supervised limits and windows

The implementation preserves:

- One approved owner
- Approved limit between 1 and 3
- Readiness freshness of 300 seconds
- Preview freshness of 300 seconds
- Authorization lifetime of 600 seconds
- Pre-send freeze freshness of 120 seconds
- Post-run review deadline of 600 seconds

The exact freshness boundaries are inclusive.

Older evidence fails closed.

## Canonical pre-send freeze fingerprint

The freeze fingerprint is a canonical SHA-256 digest binding:

- Authorization identifier
- Authorization command fingerprint
- Pilot owner identifier
- Approved limit
- Feature-gate state
- Backend-policy state
- Default-sender state
- Sender-verification state
- Provider operational state
- Provider quota
- Authorization state
- Operator identity
- Primary reviewer identity
- Secondary reviewer identity
- Rollback reviewer identity
- Incident commander identity
- Freeze timestamp

Canonical JSON uses sorted keys and compact separators.

Changing any bound field changes the fingerprint.

## Supervised execution evidence

The immutable reference evidence includes:

- Change-record identifier
- Authorization identifier
- Authorization state
- Authorization consumption state
- Authorization expiration
- Authorization command fingerprint
- Pilot owner and approved limit
- Preview owner, limit and candidate count
- Preview skip and refusal state
- Readiness state and timestamp
- Preview timestamp
- Freeze timestamp
- Provider, sender, feature-gate and backend state
- Owner opt-in and eligible-candidate state
- Concurrent-run and incident state
- Operator and reviewer identities
- Rollback reviewer and incident commander
- Both production confirmations
- Command owner and limit
- Issued execution window
- Freeze and runtime fingerprints

## Deterministic preflight evaluator

A successful preflight result contains only:

- `approved`
- `status`
- `reason_codes`
- `change_record_id`
- `authorization_id`
- `pilot_owner_id`
- `approved_limit`
- `preview_candidate_count`
- `authorization_command_fingerprint`
- `freeze_fingerprint`

The evaluator never returns credentials, recipient details, saved-search
payloads or rendered messages.

## Stable abort reasons

All 38 abort reasons remain ordered:

- `authorization_lane_not_closed`
- `invalid_owner_id`
- `invalid_pilot_limit`
- `authorization_not_authorized`
- `authorization_already_consumed`
- `authorization_expired`
- `authorization_revoked`
- `command_fingerprint_mismatch`
- `owner_binding_mismatch`
- `limit_binding_mismatch`
- `readiness_not_ready`
- `readiness_check_count_mismatch`
- `readiness_evidence_stale`
- `preview_evidence_stale`
- `pre_send_freeze_stale`
- `feature_gate_disabled`
- `email_backend_rejected`
- `default_sender_missing`
- `sender_unverified`
- `provider_credentials_unavailable`
- `provider_quota_insufficient`
- `provider_not_operational`
- `owner_opt_in_disabled`
- `no_eligible_due_candidate`
- `preview_candidate_count_invalid`
- `preview_skips_unresolved`
- `preview_unexpected_refusal`
- `concurrent_owner_run`
- `unresolved_incident`
- `operator_identity_missing`
- `primary_reviewer_missing`
- `secondary_reviewer_missing`
- `reviewer_identity_collision`
- `rollback_reviewer_missing`
- `incident_commander_missing`
- `production_confirmation_missing`
- `authorization_consumption_failed`
- `runtime_state_changed_after_freeze`

Every reason has a focused reachability test.

## Owner, limit and preview bindings

Approval requires:

- Positive owner identifier
- Limit from one through three
- Preview owner equal to approved owner
- Command owner equal to approved owner
- Preview limit equal to approved limit
- Command limit equal to approved limit
- Preview candidate count from one through the approved limit
- Positive eligible due-candidate count
- Understood preview skips
- Zero unexpected preview refusals

Any mismatch aborts the plan.

## Authorization boundary

Approval requires:

- Closed authorization lane
- Authorization state `authorized`
- Authorization not consumed
- Authorization not expired
- Authorization not revoked
- Matching canonical command fingerprint
- Successful one-shot consumption capability

The consumption helper returns `consumed` only once.

A reused authorization returns
`authorization_already_consumed`.

## Readiness and provider boundary

Approval requires:

- Strict readiness status `ready`
- Exactly nine readiness checks
- Fresh readiness evidence
- Fresh matching preview evidence
- Fresh pre-send freeze
- Enabled feature gate
- Approved backend
- Configured default sender
- Verified sender
- Available provider credentials
- Sufficient provider quota
- Operational provider
- Enabled owner opt-in
- No concurrent owner-scoped run
- No unresolved incident

## Supervision-role boundary

The implementation requires:

- Operator
- Primary reviewer
- Secondary reviewer
- Distinct primary and secondary reviewers
- Rollback reviewer
- Incident commander
- Post-run reconciliation owner

Missing or conflicting identities fail closed.

## Runtime freeze mutation protection

The evaluator compares:

- The originally recorded freeze fingerprint
- A newly computed freeze fingerprint
- The runtime-observed freeze fingerprint

Any difference returns:

`runtime_state_changed_after_freeze`

The execution plan is then aborted.

## Bounded nonexecuting plan

The reference planner returns:

- At most one authorization consumption
- At most one production invocation
- The reviewed command pattern
- Owner and limit
- Command fingerprint
- Freeze fingerprint
- Stable abort reasons

The planner does not call subprocesses, management commands, email backends or
the production sender.

The reviewed production pattern remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

v260 does not execute this command.

## One-shot consumption

The reference consumption helper:

1. Re-evaluates every preflight gate.
2. Rejects consumed, expired or revoked authorization.
3. Rejects runtime mutation after freeze.
4. Returns state `consumed` exactly once.
5. Records the consumption timestamp in a sanitized result.

It performs no delivery.

## Post-run reconciliation

The reference post-run evaluator verifies:

- Production invocation count equals one.
- Authorization consumption count equals one.
- Delivered, skipped, refused and failed counts reconcile.
- Failed count is zero.
- Unexpected refusal count is zero.
- `delivery_attempted` events reconcile.
- `delivery_succeeded` events reconcile.
- `delivery_failed` events reconcile.
- `sent_timestamp_recorded` events reconcile.
- Sent timestamps are consistent.
- Duplicate-attempt review is clean.
- Persistent audit has no gaps.
- Provider has no unexplained anomaly.
- Incident state is closed or escalated.
- Review completes within 600 seconds.
- Automatic retry remains disabled.
- Automatic rollout promotion remains disabled.

## Stable post-run reasons

The ordered post-run reasons are:

- `production_invocation_count_mismatch`
- `authorization_consumption_count_mismatch`
- `delivery_counts_mismatch`
- `failed_count_nonzero`
- `unexpected_refusal_count_nonzero`
- `delivery_attempted_event_mismatch`
- `delivery_succeeded_event_mismatch`
- `delivery_failed_event_mismatch`
- `sent_timestamp_event_mismatch`
- `sent_timestamp_inconsistent`
- `duplicate_attempt_detected`
- `audit_gap_detected`
- `provider_anomaly_detected`
- `incident_not_closed_or_escalated`
- `post_run_review_deadline_missed`
- `automatic_retry_enabled`
- `automatic_rollout_promotion_enabled`

Any reason changes the result from `closed` to `escalate`.

## Audit sequences

Successful delivery continues to require:

1. `delivery_attempted`
2. `delivery_succeeded`
3. `sent_timestamp_recorded`

Failed delivery continues to require:

1. `delivery_attempted`
2. `delivery_failed`

## Evidence sanitizer

The sanitizer retains only the v259 supervised-execution evidence allowlist.

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

## Readiness command boundary

The report-only readiness commands remain:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

and:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

They open no email connection.

## Prohibited actions

v260 continues to prohibit:

- Production delivery during this checkpoint
- Global all-owner execution
- Multi-owner execution
- Limit below one
- Limit above three
- Readiness bypass
- Preview bypass
- Authorization reuse
- Production-confirmation bypass
- Provider-verification bypass
- Runtime mutation after freeze
- Blind retry
- Automatic retry
- Automatic authorization renewal
- Automatic rollout promotion
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

v260 introduces no changes to:

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

v260 is complete only when:

- Scope is exactly two files.
- v259 remains unchanged.
- Freeze fingerprints are deterministic.
- Every freeze field remains bound.
- Every abort reason is reachable.
- Abort-reason order is deterministic.
- Freshness boundaries are enforced.
- Runtime mutation after freeze fails closed.
- Planning remains nonexecuting.
- Authorization consumption is one-shot.
- Every post-run reason is reachable.
- Post-run reason order is deterministic.
- Evidence sanitization is allowlist based.
- Sensitive evidence remains excluded.
- No production delivery occurs.
- Historical safety tests pass.
- Full regression passes.
- Working tree is clean.
- The v260 tag resolves to final HEAD.

## Next checkpoint

v261: saved-search notification production delivery pilot supervised execution closeout audit
