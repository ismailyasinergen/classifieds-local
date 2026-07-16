# v258 — Saved-Search Notification Production Delivery Pilot Execution Authorization Closeout Audit

## Checkpoint identity

- Base:
  `project-checkpoint-v257-saved-search-notification-production-delivery-pilot-execution-authorization`
- Target:
  `project-checkpoint-v258-saved-search-notification-production-delivery-pilot-execution-authorization-closeout-audit`
- Marker:
  `V258_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_EXECUTION_AUTHORIZATION_CLOSEOUT_AUDIT`

## Purpose

v258 closes the saved-search notification production-delivery
pilot-execution authorization contract and implementation lane.

The closeout audits:

- Canonical SHA-256 command fingerprints
- Owner and limit bindings
- Readiness and preview freshness
- Authorization lifetime
- Deterministic stop reasons
- Immutable binding snapshots
- Lifecycle transitions
- Terminal-state locking
- One-shot authorization consumption
- Evidence sanitization
- Runtime and schema boundaries

This checkpoint performs no production delivery.

## Exact v258 scope

v258 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_execution_authorization_closeout_audit_v258.py`
2. `docs/saved_search_notification_production_delivery_pilot_execution_authorization_closeout_audit_v258.md`

## Closed package boundary

The closeout verifies that:

- v256 remains the two-file authorization contract.
- v257 remains the two-file authorization implementation.
- v258 remains the two-file closeout audit.
- Production runtime remains unchanged.
- Scheduler remains nonautomatic.
- Schema and UI remain unchanged.
- Migration 0016 remains latest.
- Migration 0017 remains absent.

## Proposed v259 supervised-execution scope

v259 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_contract_v259.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_contract_v259.md`

v259 remains documentation and test only.

It must not perform production delivery or modify production runtime.

## Authorization limit closeout

The authorization limit remains:

- Minimum: 1
- Maximum: 3

The underlying production batch cap remains 25.

The authorization lane does not permit pilot expansion above three.

## Freshness and lifetime closeout

The closed boundaries remain:

- Readiness evidence maximum age: 300 seconds
- Preview evidence maximum age: 300 seconds
- Authorization lifetime maximum: 600 seconds

The exact 300-second freshness boundary remains valid.

Evidence older than 300 seconds remains invalid.

An authorization is expired when evaluation time reaches or exceeds its
expiration timestamp.

## Command fingerprint closeout

The command fingerprint remains the canonical SHA-256 digest of:

- `command_name`
- `execute_production_send`
- `confirm_production_delivery`
- `owner_id`
- `limit`

The fingerprint binds:

- Command identity
- Execution confirmation
- Delivery confirmation
- Owner identifier
- Approved limit

Changing any bound field changes the fingerprint.

## Authorization evaluator closeout

The deterministic evaluator returns authorization only when all gates pass.

Its sanitized result contains:

- `authorized`
- `status`
- `reason_codes`
- `authorization_id`
- `pilot_owner_id`
- `approved_limit`
- `preview_candidate_count`
- `command_fingerprint`
- `expires_at_utc`

No credential, recipient, saved-search or rendered-message payload is returned.

## Stable stop reasons

All 31 ordered stop reasons remain:

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

Reason-code order remains deterministic.

## Immutable bindings closeout

The immutable snapshot remains bound to:

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

Any binding change requires a new authorization.

## Lifecycle closeout

The allowed lifecycle remains:

1. `draft`
2. `ready_for_review`
3. `authorized`
4. `consumed`
5. `expired`
6. `revoked`
7. `failed_closed`

Terminal states remain:

- `consumed`
- `expired`
- `revoked`
- `failed_closed`

A terminal state cannot reopen.

An invalid transition remains fail-closed.

## One-shot consumption closeout

Authorization consumption remains one-shot.

The consumption helper:

1. Verifies the presented command fingerprint.
2. Re-evaluates all authorization gates.
3. Requires current state `authorized`.
4. Transitions once to `consumed`.
5. Returns a sanitized consumption result.

A second attempt returns `authorization_already_consumed`.

A fingerprint mismatch returns `command_fingerprint_mismatch` and fails closed.

The helper does not invoke the production sender.

## Preview boundary

The nonproduction preview remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

The preview contains no production flags.

Its owner and limit must match the authorization.

## Production-command boundary

The reviewed production pattern remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

v258 does not execute this command.

Both production confirmation flags remain mandatory.

## Readiness boundary

The strict-readiness command remains:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

The JSON report remains:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

All nine readiness checks remain required.

The default development configuration remains expected to report `not_ready`
because the production feature gate is disabled.

## Provider and reviewer boundary

Authorization continues to require:

- Enabled feature gate
- Approved backend
- Configured default sender
- Verified sender identity or domain
- Available provider credentials
- Sufficient provider quota
- Operational provider status
- No concurrent owner-scoped run
- No unresolved incident
- Available rollback reviewer
- Recorded operator identity
- Two nonempty reviewer identities
- Distinct reviewer identities

Any failure blocks authorization.

## Evidence allowlist closeout

The authorization evidence sanitizer remains allowlist based.

It retains only approved operational fields from the v256 contract.

Unknown fields are discarded.

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

## v259 supervised-execution preconditions

The v259 contract lane must preserve:

- The closed authorization package
- Documentation-and-test-only scope
- One positive approved owner
- A limit between one and three
- Fresh readiness evidence
- Fresh matching preview evidence
- One unconsumed authorization
- Matching command fingerprint
- Matching owner across authorization, preview and command
- Matching limit across authorization, preview and command
- Two current and distinct reviewer approvals
- Current provider and sender evidence
- No concurrent owner-scoped run
- No unresolved incident
- Available rollback reviewer
- Both production confirmation flags
- At most one authorization consumption
- Mandatory post-run reconciliation
- No automatic retry
- No automatic rollout promotion

The v259 contract itself must not execute production delivery.

## Post-run reconciliation boundary

Any future supervised invocation must reconcile:

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

Authorization consumption does not itself prove successful delivery.

## Prohibited actions

The closed authorization lane continues to prohibit:

- Production delivery during documentation-and-test checkpoints
- Authorization without a positive owner
- Authorization without an explicit limit
- Limit below one
- Limit above three
- Stale readiness evidence
- Stale preview evidence
- Authorization lifetime above 600 seconds
- Missing or identical reviewer identities
- Owner change after authorization
- Limit change after authorization
- Fingerprint change after authorization
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
- Automatic retry
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

v258 introduces no changes to:

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

- Exact clean v257 base verification
- Exact v257 two-file committed-scope verification
- v257 implementation and next-lane verification
- Host-side v258 AST validation
- Django system checks
- Migration dry-run checks
- Applied migration verification
- Category-seed verification
- Docker Compose validation
- Readiness command smoke tests
- Production command-help smoke test
- Focused v258 closeout tests
- v256-v258 authorization transition tests
- v253-v258 pilot-readiness and authorization guard tests
- Historical delivery, rollback and audit safety tests
- Complete Django regression
- Protected-file checksum verification
- Exact two-file commit-scope verification

## Closeout result

The authorization lane is closed only when:

- v256 remains unchanged.
- v257 remains unchanged.
- v258 contains exactly two files.
- Fingerprint tests pass.
- Freshness and lifetime tests pass.
- Stop-reason tests pass.
- Lifecycle tests pass.
- One-shot consumption tests pass.
- Privacy tests pass.
- Historical safety tests pass.
- Full regression passes.
- Runtime, scheduler, schema and UI remain unchanged.
- Migration 0017 remains absent.
- The v258 tag resolves to final HEAD.
- The v258 parent remains tagged v257.
- The working tree is clean.
- No production delivery occurs.
- No remote push occurs.

## Next checkpoint

v259: saved-search notification production delivery pilot supervised execution contract
