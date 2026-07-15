# v255 — Saved-Search Notification Production Delivery Pilot Readiness Closeout Audit

## Checkpoint identity

- Base:
  `project-checkpoint-v254-saved-search-notification-production-delivery-pilot-readiness`
- Target:
  `project-checkpoint-v255-saved-search-notification-production-delivery-pilot-readiness-closeout-audit`
- Marker:
  `V255_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_READINESS_CLOSEOUT_AUDIT`

## Purpose

v255 closes the saved-search notification production-delivery pilot-readiness
contract and implementation lane.

The checkpoint audits the deterministic reference evaluators, evidence
sanitizer, owner and limit constraints, command boundaries, persistent-audit
reconciliation and protected runtime boundary.

This checkpoint performs no production delivery.

## Exact v255 scope

v255 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_readiness_closeout_audit_v255.py`
2. `docs/saved_search_notification_production_delivery_pilot_readiness_closeout_audit_v255.md`

## Closed package boundary

The closeout verifies that:

- v253 remains the two-file pilot-readiness contract.
- v254 remains the two-file pilot-readiness implementation.
- v255 remains a two-file closeout audit.
- Runtime, command, scheduler, schema and UI files remain unchanged.
- Migration 0016 remains the latest listings migration.
- Migration 0017 remains absent.

## Proposed v256 authorization-contract scope

v256 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_execution_authorization_contract_v256.py`
2. `docs/saved_search_notification_production_delivery_pilot_execution_authorization_contract_v256.md`

v256 remains documentation and test only.

It must not execute production delivery or change production runtime.

## Pilot limit closeout

The pilot-readiness limit remains exactly:

- Minimum: 1
- Maximum: 3

Limits below one remain invalid.

Limits above three remain invalid for the pilot.

The underlying production batch cap remains 25, but the pilot authorization
boundary remains narrowed to no more than three candidates.

## Decision-stage closeout

The deterministic stage order remains:

1. Authorization
2. Owner eligibility
3. Environment verification
4. Strict readiness
5. Matching preview
6. Reviewer go decision
7. Guarded production invocation
8. Post-run verification

Authorization remains the first stage.

Post-run verification remains the final stage.

No stage may be skipped.

## Preflight evaluator closeout

The reference preflight evaluator remains fail-closed.

A ready result requires:

- A positive approved owner identifier
- An approved limit between one and three
- Explicit owner approval
- Explicit reviewer approval
- Isolated owner scope
- Enabled notification opt-in
- At least one eligible due saved search
- Usable recipient state
- No concurrent owner-scoped run
- No unresolved incident
- Enabled production feature gate
- Approved production email backend
- Configured default sender
- Verified sender identity or domain
- Available provider credentials
- Sufficient provider quota
- Operational provider status
- Assigned bounce and complaint ownership
- Approved execution window
- Available rollback reviewer
- Strict readiness status of `ready`
- All nine readiness checks
- Retained sanitized readiness JSON
- Reviewed deployed command help
- Source-verified rollback controls
- Preview owner matching the approved owner
- Preview limit matching the approved limit
- Preview candidate count between one and the approved limit
- Understood preview skip classifications
- Zero unexpected preview refusals

Any missing condition produces `not_ready`.

## Stable preflight reason codes

The 30 ordered preflight reason codes remain:

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

The order remains deterministic.

## Sanitized preflight result

The preflight result retains only:

- `ready`
- `status`
- `reason_codes`
- `owner_id`
- `approved_limit`
- `preview_candidate_count`

It contains no credential, recipient, sender, saved-search or rendered-message
payload.

## Strict readiness boundary

The reviewed strict-readiness command remains:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

The command must report `ready` before authorization.

All nine stable readiness checks must remain present.

The default local configuration remains expected to report `not_ready` because
the production feature gate is disabled.

## Sanitized readiness evidence

The reviewed JSON command remains:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

Retained evidence is limited to:

- Overall status
- Stable check identifiers
- Stable reason codes
- Ready count
- Not-ready count
- Warning count

Raw configuration values remain excluded.

## Deployed command verification

The deployed command surface must be reviewed with:

    docker compose exec -T web python manage.py process_saved_search_notifications --help

Required controls remain:

- `--execute-production-send`
- `--confirm-production-delivery`
- `--owner-id`
- `--limit`

A command-surface mismatch blocks authorization.

## Matching preview boundary

The reviewed nonproduction preview remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

The preview:

- Targets one approved owner.
- Uses the approved limit.
- Contains no production confirmation flags.
- Returns at least one candidate.
- Does not exceed the approved limit.
- Produces understood classifications.
- Produces zero unexpected refusals.

Owner or limit changes after preview require a fresh preview and fresh review.

## Guarded production-command boundary

The reviewed production pattern remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

v255 does not execute this command.

Any future authorization must preserve:

- Both production confirmation flags
- The previewed owner
- The previewed limit
- A limit between one and three
- At most one authorized invocation

## Evidence allowlist closeout

The evidence sanitizer remains allowlist based.

Approved fields include:

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
- Readiness status and counts
- Preview counts
- Production counts
- Audit verification
- Sent-timestamp verification
- Duplicate-attempt verification
- Rollback-readiness verification
- Decision
- Incident reference

Unknown fields remain discarded.

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

Suspected private-data or secret exposure blocks authorization.

## Post-run evaluator closeout

A successful post-run result continues to require:

- Failed count equals zero.
- Unexpected refusal count equals zero.
- Delivered, skipped, refused and failed counts reconcile.
- `delivery_attempted` event count reconciles.
- `delivery_succeeded` event count reconciles.
- `delivery_failed` event count reconciles.
- `sent_timestamp_recorded` event count reconciles.
- Sent-timestamp evidence is consistent.
- Duplicate-attempt review is clean.
- No audit gap exists.
- No provider anomaly exists.
- No incident remains open.

Understood skipped candidates may coexist with success when all counts reconcile.

## Stable post-run reason codes

The 12 ordered post-run reason codes remain:

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

Any reason code means the pilot is not successful.

## Persistent audit closeout

The read-only audit interface remains:

    /staff/saved-search-notification-audit/

Successful delivery evidence remains:

1. `delivery_attempted`
2. `delivery_succeeded`
3. `sent_timestamp_recorded`

Failed delivery evidence remains:

1. `delivery_attempted`
2. `delivery_failed`

Audit rows remain append-only.

Manual audit-row editing or deletion remains prohibited.

## Rollback-readiness closeout

Before future authorization, verify:

- Deployed command help
- Source-supported rollback controls
- Rollback reviewer availability
- Existing rollback preview workflow
- Owner and attempt selection
- Post-rollback audit verification
- Restored timestamp verification
- Unrelated timestamp preservation

Do not invent rollback flags.

Do not use direct SQL repair.

Do not use Django shell timestamp repair.

## v256 authorization preconditions

The v256 authorization-contract lane must preserve:

- The closed pilot-readiness package
- Documentation-and-test-only scope
- One positive approved owner
- A pilot limit between one and three
- Time-bounded owner and limit approval
- Fresh strict-readiness evidence
- Fresh sanitized readiness JSON
- A fresh matching owner-scoped preview
- Candidate count between one and the approved limit
- Current provider and sender verification
- No concurrent owner-scoped run
- No unresolved incident
- An available rollback reviewer
- Both production confirmation flags
- Authorization for at most one invocation
- No automatic phase promotion

Authorization must not itself execute production delivery.

## Prohibited actions

The closed pilot-readiness lane continues to prohibit:

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

v255 introduces no changes to:

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

- Exact clean v254 base verification
- v254 exact two-file committed-scope verification
- v254 package and next-lane verification
- Host-side v255 AST validation
- Django system checks
- Migration dry-run checks
- Applied migration verification
- Category-seed verification
- Docker Compose validation
- Readiness command smoke tests
- Production command-help smoke test
- Focused v255 closeout tests
- v253-v255 pilot-readiness transition tests
- v250-v255 controlled-rollout and pilot-readiness guard tests
- Historical production-delivery safety tests
- Complete Django regression
- Protected-file checksum verification
- Exact two-file commit-scope verification

## Closeout result

The pilot-readiness lane is closed only when:

- v253 remains unchanged.
- v254 remains unchanged.
- v255 contains exactly two files.
- Focused tests pass.
- Historical safety tests pass.
- Full regression passes.
- Runtime, scheduler, schema and UI remain unchanged.
- Migration 0017 remains absent.
- The v255 tag resolves to final HEAD.
- The v255 parent remains the tagged v254 checkpoint.
- The working tree is clean.
- No production delivery occurs.
- No remote push occurs.

## Next checkpoint

v256: saved-search notification production delivery pilot execution authorization contract
