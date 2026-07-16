# v259 — Saved-Search Notification Production Delivery Pilot Supervised Execution Contract

## Checkpoint identity

- Base:
  `project-checkpoint-v258-saved-search-notification-production-delivery-pilot-execution-authorization-closeout-audit`
- Target:
  `project-checkpoint-v259-saved-search-notification-production-delivery-pilot-supervised-execution-contract`
- Marker:
  `V259_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_CONTRACT`

## Purpose

v259 defines the contract for a single tightly supervised saved-search
notification production pilot invocation.

This checkpoint performs no production delivery.

The contract is documentation and test only.

## Exact v259 scope

v259 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_contract_v259.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_contract_v259.md`

## Proposed v260 implementation scope

v260 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_v260.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_v260.md`

v260 remains documentation and test only.

It must not execute production delivery or change production runtime.

## Supervised-execution objective

A supervised execution binds one guarded production-command invocation to:

- One approved owner
- One limit between one and three
- One fresh strict-readiness report
- One fresh matching preview
- One valid unconsumed authorization
- One matching command fingerprint
- One short pre-send freeze
- Two distinct reviewers
- One rollback reviewer
- One incident commander
- One mandatory post-run reconciliation

The contract permits no automatic retry or automatic rollout promotion.

## Pilot limit boundary

The supervised pilot limit remains:

- Minimum: 1
- Maximum: 3

The underlying production batch cap remains 25.

The supervised lane cannot expand the pilot above three.

## Time-window boundary

The contract defines:

- Readiness evidence maximum age: 300 seconds
- Preview evidence maximum age: 300 seconds
- Authorization lifetime: 600 seconds
- Pre-send freeze maximum age: 120 seconds
- Post-run review deadline: 600 seconds

Stale evidence blocks execution.

A runtime-state change after the pre-send freeze blocks execution.

## Required supervision roles

The supervised change window requires:

- Operator
- Primary reviewer
- Secondary reviewer
- Rollback reviewer
- Incident commander

Primary and secondary reviewer identities must be distinct.

Each role must be recorded before execution.

## Deterministic stage order

The required stage order is:

1. Open the supervised change window.
2. Verify immutable authorization bindings.
3. Rerun strict readiness.
4. Rerun the matching owner-scoped preview.
5. Freeze provider, sender, owner and limit state.
6. Record the final reviewer go decision.
7. Consume authorization exactly once.
8. Invoke one guarded production command.
9. Capture persistent audit and timestamp evidence.
10. Perform mandatory post-run reconciliation.
11. Close or escalate the change window.

No stage may be skipped.

## Immutable execution bindings

After final review, these values cannot change:

- Change-record identifier
- Authorization identifier
- Authorization command fingerprint
- Pilot owner identifier
- Approved limit
- Preview owner identifier
- Preview limit
- Preview candidate count
- Operator identity
- Primary reviewer identity
- Secondary reviewer identity
- Issued execution window

Any change requires a fresh authorization and fresh review.

## Authorization boundary

The supervised invocation requires:

- Authorization state `authorized`
- Authorization not previously consumed
- Authorization not expired
- Authorization not revoked
- Matching command fingerprint
- Matching owner
- Matching limit
- Authorization consumption exactly once

An authorization cannot be reused.

Consumption failure blocks the production invocation.

## Strict readiness boundary

The strict-readiness command remains:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

Execution requires:

- Status `ready`
- All nine readiness checks
- Readiness evidence no older than 300 seconds
- No active incident
- No command-surface mismatch

The sanitized JSON command remains:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

Raw secrets and configuration values must not be retained.

## Matching preview boundary

The nonproduction preview remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

The preview must:

- Target the approved owner.
- Use the approved limit.
- Contain no production confirmation flags.
- Return at least one candidate.
- Not exceed the approved limit.
- Have understood skip classifications.
- Have zero unexpected refusals.
- Be no older than 300 seconds.

An owner or limit change requires a new preview.

## Pre-send freeze

Immediately before final approval, freeze and record:

- Owner identifier
- Limit
- Command fingerprint
- Feature-gate state
- Email-backend policy
- Sender-verification state
- Provider operational state
- Provider quota verification
- Authorization state
- Reviewer identities
- Rollback-reviewer availability
- Incident-commander availability

The freeze is valid for no more than 120 seconds.

Any state mutation after the freeze aborts execution.

## Provider and sender boundary

Execution requires current confirmation that:

- The feature gate is enabled.
- The approved email backend is configured.
- The default sender is configured.
- Sender identity or domain is verified.
- Provider credentials are available outside retained evidence.
- Provider quota covers the approved limit.
- Provider status is operational.
- Bounce and complaint ownership remains assigned.

Provider or sender degradation aborts execution.

## Final reviewer decision

The final go decision must apply to the same:

- Owner
- Limit
- Preview
- Authorization
- Command fingerprint
- Provider state
- Sender state
- Execution window

Both primary and secondary reviewers must explicitly approve.

Reviewer identity collision blocks execution.

## Guarded production-command boundary

The reviewed production pattern remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

v259 does not execute this command.

A future supervised invocation must preserve:

- `--execute-production-send`
- `--confirm-production-delivery`
- The approved owner
- The approved limit
- A limit between one and three
- Exactly one production-command invocation

## Abort reasons

Execution fails closed for:

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

Any abort reason blocks execution.

## Persistent audit boundary

A successful delivery must retain this audit sequence:

1. `delivery_attempted`
2. `delivery_succeeded`
3. `sent_timestamp_recorded`

A failed delivery must retain:

1. `delivery_attempted`
2. `delivery_failed`

Audit rows remain append-only.

Manual audit-row editing or deletion is prohibited.

## Post-run reconciliation

Post-run review must verify:

- Production invocation count equals one.
- Authorization consumption count equals one.
- Delivered, skipped, refused and failed counts reconcile.
- Failed count equals zero for success.
- Unexpected refusal count equals zero for success.
- `delivery_attempted` count reconciles.
- `delivery_succeeded` count reconciles.
- `delivery_failed` count reconciles.
- `sent_timestamp_recorded` count reconciles.
- Sent timestamps are consistent.
- Duplicate-attempt review is clean.
- Persistent audit has no gaps.
- Provider has no unexplained anomaly.
- Incident state is closed or explicitly escalated.
- Review completes within 600 seconds.
- Automatic retry remains disabled.
- Automatic rollout promotion remains disabled.

Authorization consumption alone does not prove delivery success.

## Evidence package

Retained evidence is restricted to approved operational fields including:

- Change-record and authorization identifiers
- Owner and approved limit
- Preview candidate count
- Readiness status and counts
- Readiness and preview timestamps
- Pre-send freeze timestamp
- Authorization-consumption timestamp
- Production start and finish timestamps
- Operator and reviewer identities
- Rollback reviewer and incident commander
- Provider and sender states
- Feature-gate and backend-policy verification
- Delivery and audit counts
- Sent-timestamp consistency
- Duplicate-attempt status
- Audit-gap status
- Provider-anomaly status
- Final decision
- Stable reason codes
- Incident reference

Unknown fields are discarded.

## Privacy and secret boundary

Never retain:

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

Suspected exposure aborts execution and opens an incident.

## Rollback boundary

Before invocation, verify:

- Rollback reviewer availability
- Existing rollback preview workflow
- Owner and attempt selection
- Expected audit linkage
- Sent-timestamp restoration verification
- Unrelated timestamp preservation

Do not invent rollback flags.

Do not use direct SQL repair.

Do not use Django shell timestamp repair.

## Incident boundary

The incident commander must be ready to act on:

- Provider degradation
- Sender-verification change
- Unexpected refusal
- Delivery failure
- Audit gap
- Sent-timestamp mismatch
- Duplicate-attempt anomaly
- Privacy or secret exposure
- Authorization-consumption inconsistency
- Runtime-state mutation after freeze

An open incident prevents rollout promotion.

## Prohibited actions

The supervised-execution contract prohibits:

- Production delivery during the contract checkpoint
- Execution without a positive owner identifier
- Execution without an explicit limit
- Limit below one
- Limit above three
- Stale readiness evidence
- Stale preview evidence
- Invalid or consumed authorization
- Command-fingerprint mismatch
- Execution after authorization expiration
- Execution after authorization revocation
- Authorization reuse
- Owner change after pre-send freeze
- Limit change after pre-send freeze
- Provider change after pre-send freeze
- Sender change after pre-send freeze
- Missing or identical reviewer identities
- Missing rollback reviewer
- Missing incident commander
- Global all-owner execution
- Multi-owner execution
- Readiness bypass
- Preview bypass
- Production-confirmation bypass
- Provider-verification bypass
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

v259 and proposed v260 introduce no changes to:

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

v260 is accepted only when:

- Its scope is exactly the two contracted files.
- Supervised evaluation is deterministic.
- All abort reasons are stable and ordered.
- Owner and limit boundaries are enforced.
- Readiness and preview freshness are enforced.
- Pre-send freeze freshness is enforced.
- Authorization is consumed at most once.
- Runtime mutation after freeze fails closed.
- Reviewer and supervision roles are enforced.
- Production invocation count is bounded to one.
- Post-run reconciliation is deterministic.
- Evidence is allowlist sanitized.
- Sensitive fields remain excluded.
- No production delivery occurs.
- Runtime, scheduler, schema and UI remain unchanged.
- Historical safety tests pass.
- Full regression remains green.

## Next checkpoint

v260: saved-search notification production delivery pilot supervised execution implementation
