# v253 — Saved-Search Notification Production Delivery Pilot Readiness Contract

## Checkpoint identity

- Base:
  `project-checkpoint-v252-saved-search-notification-production-delivery-controlled-rollout-closeout-audit`
- Target:
  `project-checkpoint-v253-saved-search-notification-production-delivery-pilot-readiness-contract`
- Marker:
  `V253_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_READINESS_CONTRACT`

## Purpose

v253 defines the readiness contract that must be satisfied before the first
single-owner production pilot may be authorized.

This checkpoint does not send email.

It adds only a contract test and this root document.

## Exact v253 scope

v253 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_readiness_contract_v253.py`
2. `docs/saved_search_notification_production_delivery_pilot_readiness_contract_v253.md`

## Proposed v254 implementation scope

v254 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_readiness_v254.py`
2. `docs/saved_search_notification_production_delivery_pilot_readiness_v254.md`

The v254 implementation remains documentation and test only.

It must not change runtime, commands, scheduler, schema or UI.

## Pilot safety objective

The pilot readiness lane answers one question:

Is one explicitly approved owner ready for one explicitly bounded production
pilot containing between one and three eligible saved-search notifications?

A readiness decision does not itself authorize delivery.

A separate reviewer go decision remains required immediately before any pilot
production invocation.

## Pilot limit boundary

The pilot limit band is exactly:

- Minimum: 1
- Maximum: 3

A limit of zero is not a production pilot.

A limit above three is not authorized by the pilot-readiness lane.

The underlying production batch maximum remains 25, but the pilot contract
narrows the initial production scope to a maximum of three.

## Pilot owner eligibility

The selected owner is eligible only when:

- A positive owner identifier is recorded.
- Owner approval is explicit.
- The owner scope can be isolated.
- The owner has enabled saved-search notification opt-in.
- At least one eligible due saved search exists.
- A usable recipient address exists in current application data.
- Candidate count fits within one through three.
- No concurrent run targets the same owner.
- No unresolved delivery incident targets the owner.
- No unresolved rollback incident targets the owner.
- Owner and limit approval remain valid for the execution window.

The contract retains only the approved owner identifier, not the recipient
email address.

## Production environment evidence

Before pilot authorization, verify:

- The production-delivery feature gate is explicitly enabled.
- An approved production email backend is configured.
- A default sender is configured.
- The sender identity or domain is verified by the provider.
- Provider credentials are available through the approved secret-management
  path and are not copied into retained evidence.
- The provider quota is sufficient for no more than three deliveries.
- Provider status is operational.
- Responsibility for bounce and complaint review is assigned.
- The execution window is approved.
- A rollback reviewer is available.

Provider credentials, sender values and backend paths must not appear in the
evidence package.

## Strict readiness gate

Run immediately before preview:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

The command must report `ready`.

All nine readiness checks must remain present.

A nonzero strict-readiness exit or any `not_ready` result is an immediate stop.

## Sanitized readiness evidence

Capture:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

Retain only:

- Overall status
- Stable check identifiers
- Stable reason codes
- Ready count
- Not-ready count
- Warning count

Do not retain raw configuration values.

## Deployed command verification

Before preview, inspect the deployed production command:

    docker compose exec -T web python manage.py process_saved_search_notifications --help

Verify that deployed help exposes:

- `--execute-production-send`
- `--confirm-production-delivery`
- `--owner-id`
- `--limit`

If deployed help differs from the reviewed command surface, stop.

## Pilot preview

The pilot preview pattern is:

    docker compose exec -T web python manage.py process_saved_search_notifications --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

The preview must:

- Target the approved owner.
- Use the approved limit.
- Contain no production confirmation flags.
- Return at least one candidate.
- Return no more candidates than the approved limit.
- Produce understood skip classifications.
- Produce no unexpected refusal.
- Produce sanitized output.

A zero-candidate preview is not ready for production pilot execution.

## Pilot go decision

A reviewer may issue a pilot go decision only when:

- Strict readiness passed immediately before preview.
- Sanitized readiness JSON was retained.
- The approved owner remained unchanged.
- The approved limit remained unchanged.
- Preview owner matched the approved owner.
- Preview limit matched the approved limit.
- Candidate count was between one and three.
- Preview classifications were understood.
- Provider status remained operational.
- No concurrent owner-scoped run was detected.
- No incident remained open.
- Rollback controls were source verified.
- The reviewer explicitly approved one pilot invocation.

A go decision authorizes at most one production command before post-run review.

## Pilot production command boundary

The guarded pilot production pattern is:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

The production command must use:

- Both production confirmation flags
- The same owner used in preview
- The same limit used in preview
- A limit from one through three

The v253 contract checkpoint must not execute this command.

## Post-run success gate

A successful pilot requires:

- Failed count equals zero.
- Unexpected refusal count equals zero.
- Delivery counts reconcile.
- `delivery_attempted` exists.
- `delivery_succeeded` exists for each successful delivery.
- `sent_timestamp_recorded` exists for each successful delivery.
- Sent-timestamp evidence is consistent.
- No sent timestamp exists for a failed item.
- Duplicate-attempt review is clean.
- No unexplained audit gap exists.
- No provider anomaly exists.
- No privacy or secret incident remains open.
- A reviewer records a go or stop decision.

Success does not automatically authorize Phase 2 expansion.

## Persistent audit verification

The read-only audit interface remains:

    /staff/saved-search-notification-audit/

For each successful pilot item verify:

1. `delivery_attempted`
2. `delivery_succeeded`
3. `sent_timestamp_recorded`

For any failed item verify:

1. `delivery_attempted`
2. `delivery_failed`

Also verify:

- Correct owner scope
- Correct attempt identity
- Stable sanitized reason code
- Correct event order
- Terminal event presence
- No unexplained audit gap
- No unexpected duplicate attempt
- No sent timestamp after failure

Audit rows remain append-only.

## Rollback readiness

Before authorizing the pilot:

- Verify deployed command help.
- Verify source-supported rollback controls.
- Identify the rollback reviewer.
- Confirm the existing rollback preview workflow.
- Confirm how affected owner and attempt identity will be selected.
- Confirm post-rollback audit verification.
- Confirm restored timestamp verification.
- Confirm unrelated timestamps will be checked.

Do not invent rollback flags.

Do not use direct SQL or Django shell timestamp repair.

## Mandatory stop conditions

Stop when:

- Readiness is not `ready`.
- One or more readiness checks are absent.
- The feature gate is disabled.
- The email backend is rejected.
- The default sender is missing.
- Sender identity or domain is unverified.
- Provider status is degraded or unknown.
- Provider quota is insufficient.
- Owner eligibility is incomplete.
- Owner authorization is missing.
- Owner scope cannot be isolated.
- Limit is outside one through three.
- Preview owner differs from approved owner.
- Preview limit differs from approved limit.
- Preview candidate count is zero.
- Preview candidate count exceeds the approved limit.
- Preview classifications are not understood.
- Another operator may be running the same owner scope.
- Configuration refusal occurs.
- Delivery failure occurs.
- Persistent audit evidence is incomplete.
- Sent-timestamp evidence is inconsistent.
- Duplicate-attempt protection activates unexpectedly.
- Provider behavior is unexpected.
- Sanitized counts cannot be reconciled.
- An unknown reason code appears.
- Private data or a secret may have appeared.
- An incident remains open.

## Pilot evidence package

Record:

- `change_record_id`
- `pilot_owner_id`
- `approved_limit`
- `operator_identity`
- `reviewer_identity`
- `execution_window`
- `started_at_utc`
- `finished_at_utc`
- `feature_gate_verified`
- `backend_policy_verified`
- `sender_verification_status`
- `provider_status`
- `provider_quota_verified`
- `readiness_status`
- `readiness_ready_count`
- `readiness_not_ready_count`
- `readiness_warning_count`
- `preview_candidate_count`
- `preview_skipped_count`
- `production_delivered_count`
- `production_skipped_count`
- `production_refused_count`
- `production_failed_count`
- `audit_verified`
- `sent_timestamp_verified`
- `duplicate_attempt_verified`
- `rollback_readiness_verified`
- `decision`
- `incident_reference`

The contract checkpoint records no actual production result because it performs
no delivery.

## Privacy and secret boundary

Never retain:

- SMTP passwords
- Confidential SMTP usernames
- API keys
- Access tokens
- Recipient email addresses
- Default sender values
- Raw backend paths
- Saved-search names
- Saved-search querystrings
- Rendered email subjects
- Rendered email bodies
- Provider response bodies
- Raw exception tracebacks

Suspected exposure blocks pilot authorization.

## Prohibited actions

The pilot-readiness contract prohibits:

- Production delivery during the contract checkpoint
- Pilot execution without explicit owner approval
- Pilot execution without reviewer approval
- Pilot limit above three
- Pilot limit below one
- Global all-owner execution
- Multi-owner command execution
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

v253 and the proposed v254 implementation introduce no changes to:

- Settings
- Production sender
- Production delivery command
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

v254 is accepted only when:

- Its scope is exactly the two contracted files.
- Pilot owner eligibility is implemented as an operator checklist.
- Environment evidence is implemented as an operator checklist.
- Pilot limit remains one through three.
- Strict readiness and sanitized JSON evidence remain mandatory.
- Provider and sender verification remain mandatory.
- Preview and production owner and limit must match.
- Production retains both confirmation flags.
- Go, success and stop gates remain explicit.
- Persistent audit, timestamp and duplicate-attempt verification remain
  mandatory.
- Rollback readiness remains explicit.
- No production command is executed by tests or documentation scripts.
- Runtime, scheduler, schema and UI remain unchanged.
- Focused and historical tests pass.
- Full regression remains green.

## Next checkpoint

v254: saved-search notification production delivery pilot readiness implementation
