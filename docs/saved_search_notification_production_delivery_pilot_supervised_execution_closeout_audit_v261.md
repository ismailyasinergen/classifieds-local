# v261 — Saved-Search Notification Production Delivery Pilot Supervised Execution Closeout Audit

## Checkpoint identity

- Base:
  `project-checkpoint-v260-saved-search-notification-production-delivery-pilot-supervised-execution`
- Target:
  `project-checkpoint-v261-saved-search-notification-production-delivery-pilot-supervised-execution-closeout-audit`
- Marker:
  `V261_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_CLOSEOUT_AUDIT`

## Purpose

v261 closes the saved-search notification production-delivery pilot
supervised-execution contract and reference-implementation lane.

The closeout audits:

- Supervised execution boundaries
- Canonical SHA-256 freeze fingerprints
- All 38 preflight abort reasons
- One-shot authorization consumption
- A nonexecuting one-invocation plan
- All 17 post-run reconciliation reasons
- Persistent audit sequences
- Evidence privacy and sanitization
- Runtime, scheduler, schema and UI protection

This checkpoint performs no production delivery.

## Exact v261 scope

v261 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_closeout_audit_v261.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_closeout_audit_v261.md`

## Closed package boundary

The closed package consists of:

- v259: supervised-execution contract
- v260: deterministic reference implementation
- v261: closeout audit

Each checkpoint remains exactly two files.

No runtime file is part of the closed package.

## Proposed v262 evidence-review scope

v262 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_evidence_review_contract_v262.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_evidence_review_contract_v262.md`

v262 remains documentation and test only.

It must not execute production delivery or change runtime behavior.

## Supervised limit closeout

The closed pilot boundaries remain:

- One approved owner
- Minimum limit: 1
- Maximum limit: 3
- Underlying production batch cap: 25

The supervised lane cannot expand above three candidates.

## Time-window closeout

The closed time windows remain:

- Readiness maximum age: 300 seconds
- Preview maximum age: 300 seconds
- Authorization lifetime: 600 seconds
- Pre-send freeze maximum age: 120 seconds
- Post-run review deadline: 600 seconds

The exact upper boundaries remain inclusive.

Older or future-invalid evidence fails closed.

## Supervision-role closeout

Required roles remain:

- Operator
- Primary reviewer
- Secondary reviewer
- Rollback reviewer
- Incident commander

Primary and secondary reviewers must remain distinct.

All role identities are bound before an executable plan may be produced.

## Deterministic stage-order closeout

The eleven stages remain:

1. Open the supervised change window.
2. Verify immutable authorization bindings.
3. Rerun strict readiness.
4. Rerun matching preview.
5. Freeze provider, sender, owner and limit state.
6. Record final reviewer go decision.
7. Consume authorization exactly once.
8. Invoke one guarded production command.
9. Capture persistent audit and timestamp evidence.
10. Perform mandatory post-run reconciliation.
11. Close or escalate the change window.

No stage may be skipped.

## Canonical freeze fingerprint closeout

The freeze fingerprint remains a canonical SHA-256 digest.

It binds:

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
- Pre-send freeze timestamp

Changing any field changes the fingerprint.

## Preflight evaluator closeout

A successful preflight result remains sanitized to:

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

No credentials, recipient information, saved-search payload or rendered
message is returned.

## Stable abort-reason closeout

All 38 ordered abort reasons remain:

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

Every abort reason remains reachable and ordered deterministically.

## Authorization-consumption closeout

Authorization consumption remains one-shot.

The helper:

1. Re-evaluates the entire preflight.
2. Requires state `authorized`.
3. Rejects previously consumed authorization.
4. Rejects expiration and revocation.
5. Rejects fingerprint mismatch.
6. Rejects runtime mutation after freeze.
7. Returns `consumed` at most once.

A repeated attempt returns:

`authorization_already_consumed`

The helper performs no production delivery.

## Runtime freeze-mutation closeout

The implementation compares:

- Recorded freeze fingerprint
- Newly calculated freeze fingerprint
- Runtime-observed freeze fingerprint

Any difference returns:

`runtime_state_changed_after_freeze`

The execution plan then contains no production command.

## Nonexecuting plan closeout

An approved reference plan contains:

- At most one authorization consumption
- At most one production invocation
- One owner
- One limit between one and three
- One command fingerprint
- One freeze fingerprint
- The reviewed production-command pattern

The planner never invokes subprocesses, management commands, the production
sender or an email connection.

The reviewed command pattern remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

v261 does not execute this command.

## Readiness boundary

The strict report-only readiness command remains:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

The JSON command remains:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

All nine readiness checks remain required.

The readiness command opens no email connection.

The default development configuration remains safely `not_ready` because the
production feature gate is disabled.

## Provider and sender boundary

Preflight approval continues to require:

- Enabled production feature gate
- Approved email backend
- Configured default sender
- Verified sender identity or domain
- Available provider credentials
- Provider quota covering the approved limit
- Operational provider state
- Enabled owner opt-in
- No concurrent owner-scoped run
- No unresolved incident

Provider or sender degradation fails closed.

## Post-run reconciliation closeout

Post-run reconciliation continues to verify:

- Production invocation count equals one.
- Authorization consumption count equals one.
- Delivery outcome counts reconcile.
- Failed count equals zero for success.
- Unexpected refusal count equals zero.
- Attempted audit events reconcile.
- Succeeded audit events reconcile.
- Failed audit events reconcile.
- Sent-timestamp audit events reconcile.
- Sent timestamps are consistent.
- Duplicate-attempt review is clean.
- Persistent audit has no gaps.
- Provider has no unexplained anomaly.
- Incident state is closed or escalated.
- Review completes within 600 seconds.
- Automatic retry remains disabled.
- Automatic rollout promotion remains disabled.

## Stable post-run reasons

All 17 ordered post-run reasons remain:

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

Any reason changes the decision from `closed` to `escalate`.

## Persistent audit sequences

Successful delivery evidence remains:

1. `delivery_attempted`
2. `delivery_succeeded`
3. `sent_timestamp_recorded`

Failed delivery evidence remains:

1. `delivery_attempted`
2. `delivery_failed`

Audit records remain append-only.

## Evidence sanitizer closeout

The evidence sanitizer remains strict allowlist based.

Unknown fields are discarded.

Only approved operational evidence is retained.

## Sensitive evidence exclusions

The sanitizer continues to exclude:

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

## v262 evidence-review preconditions

The v262 contract lane must require:

- Closed supervised-execution package
- Documentation-and-test-only scope
- One change-record identifier
- One authorization identifier
- One positive owner identifier
- Limit between one and three
- Freeze fingerprint
- Authorization command fingerprint
- Known authorization-consumption count
- Known production-invocation count
- Known delivery outcome counts
- Known persistent-audit counts
- Known sent-timestamp consistency
- Known duplicate-attempt status
- Known provider-anomaly status
- Known incident state
- Applied privacy sanitizer
- Disabled automatic retry
- Disabled automatic rollout promotion
- No production delivery during evidence review

## Evidence-review decision boundary

A future evidence-review contract may classify evidence as:

- Complete and internally consistent
- Incomplete
- Inconsistent
- Privacy-rejected
- Incident-escalated
- Not eligible for rollout consideration

Evidence review must not itself:

- Send email
- Consume another authorization
- Retry a delivery
- Promote rollout automatically
- Modify timestamps
- Delete audit events
- Repair data through direct SQL or Django shell

## Prohibited actions

The closed supervised-execution lane continues to prohibit:

- Production delivery during documentation-and-test checkpoints
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

v261 introduces no changes to:

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

## Validation matrix

The checkpoint must pass:

- Exact clean v260 base verification
- Exact v260 two-file commit-scope verification
- v260 implementation and next-lane verification
- Host-side AST validation
- Django system checks
- Migration dry-run checks
- Applied migration verification
- Category-seed verification
- Docker Compose validation
- Readiness command smoke tests
- Production-command help smoke test
- Focused v261 closeout tests
- v259-v261 transition tests
- v256-v261 authorization and supervision guard
- Historical delivery, readiness, rollback and audit safety guard
- Complete Django regression
- Protected-file checksum verification
- Exact two-file commit-scope verification

## Closeout result

The supervised-execution lane is closed only when:

- v259 remains unchanged.
- v260 remains unchanged.
- v261 contains exactly two files.
- All fingerprint tests pass.
- All 38 abort reasons remain reachable.
- One-shot consumption tests pass.
- Nonexecuting plan tests pass.
- All 17 post-run reason tests pass.
- Privacy tests pass.
- Historical safety tests pass.
- Full regression passes.
- Runtime, scheduler, schema and UI remain unchanged.
- Migration 0017 remains absent.
- The v261 tag resolves to final HEAD.
- The v261 parent remains tagged v260.
- The working tree is clean.
- No production delivery occurs.
- No remote push occurs.

## Next checkpoint

v262: saved-search notification production delivery pilot supervised execution evidence review contract
