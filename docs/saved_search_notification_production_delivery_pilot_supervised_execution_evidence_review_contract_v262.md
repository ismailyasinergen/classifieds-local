# v262 — Saved-Search Notification Production Delivery Pilot Supervised Execution Evidence Review Contract

## Checkpoint identity

- Base:
  `project-checkpoint-v261-saved-search-notification-production-delivery-pilot-supervised-execution-closeout-audit`
- Target:
  `project-checkpoint-v262-saved-search-notification-production-delivery-pilot-supervised-execution-evidence-review-contract`
- Marker:
  `V262_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_EVIDENCE_REVIEW_CONTRACT`

## Purpose

v262 defines the contract for reviewing sanitized evidence from a supervised
saved-search notification production pilot.

The review determines whether the evidence is complete, internally consistent,
privacy-safe and suitable only for manual rollout consideration.

This checkpoint:

- Performs no production delivery
- Consumes no authorization
- Retries no delivery
- Modifies no timestamp
- Deletes no audit event
- Promotes no rollout automatically

## Exact v262 scope

v262 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_evidence_review_contract_v262.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_evidence_review_contract_v262.md`

## Proposed v263 implementation scope

v263 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_evidence_review_v263.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_evidence_review_v263.md`

v263 remains documentation and test only.

It must not execute production delivery or alter production runtime.

## Closed supervised-execution dependency

Evidence review requires the closed v259–v261 supervised-execution package:

- v259 contract
- v260 reference implementation
- v261 closeout audit

The review may consume only sanitized evidence produced under that closed
boundary.

## Evidence-review preconditions

The review requires:

1. Closed supervised-execution lane
2. Documentation-and-test-only review scope
3. One change-record identifier
4. One authorization identifier
5. One positive owner identifier
6. Approved limit between one and three
7. Freeze fingerprint
8. Authorization command fingerprint
9. Known authorization-consumption count
10. Known production-invocation count
11. Known delivery outcome counts
12. Known persistent-audit counts
13. Known sent-timestamp consistency
14. Known duplicate-attempt status
15. Known provider-anomaly status
16. Known incident state
17. Applied privacy sanitizer
18. Disabled automatic retry
19. Disabled automatic rollout promotion
20. No production delivery during review

## Required evidence fields

The contract requires explicit evidence for:

- Change record
- Authorization
- Owner and limit
- Authorization command fingerprint
- Freeze fingerprint
- Authorization-consumption count
- Production-invocation count
- Delivered count
- Skipped count
- Refused count
- Failed count
- Attempted audit-event count
- Succeeded audit-event count
- Failed audit-event count
- Sent-timestamp audit-event count
- Sent-timestamp consistency
- Duplicate-attempt status
- Audit-gap status
- Provider-anomaly status
- Incident state
- Privacy-sanitizer state
- Automatic-retry state
- Automatic-rollout-promotion state
- Reviewer identity
- Review timestamp
- Final decision
- Stable reason codes

Missing required evidence prevents a complete-consistent classification.

## Immutable evidence bindings

The following values remain immutable during review:

- Change-record identifier
- Authorization identifier
- Pilot owner identifier
- Approved limit
- Authorization command fingerprint
- Freeze fingerprint

A binding mismatch produces an inconsistent classification.

Evidence review cannot repair or replace a binding.

## Decision classifications

The contract defines:

- `privacy_rejected`
- `incident_escalated`
- `incomplete`
- `inconsistent`
- `complete_consistent`
- `not_eligible_for_rollout_consideration`

Decision precedence is:

1. `privacy_rejected`
2. `incident_escalated`
3. `incomplete`
4. `inconsistent`
5. `not_eligible_for_rollout_consideration`
6. `complete_consistent`

A complete-consistent result permits only manual consideration.

It does not enable or promote rollout.

## Rollout recommendations

Evidence review may return only:

- `not_eligible`
- `eligible_for_manual_consideration`

No review result may automatically:

- Increase the owner scope
- Increase the pilot limit
- Enable the scheduler
- Enable automatic retries
- Promote a rollout phase
- Execute another production command

## Completeness reasons

The ordered completeness reasons are:

- `missing_change_record_id`
- `missing_authorization_id`
- `missing_owner_id`
- `missing_approved_limit`
- `missing_authorization_command_fingerprint`
- `missing_freeze_fingerprint`
- `missing_authorization_consumption_count`
- `missing_production_invocation_count`
- `missing_delivery_outcome_counts`
- `missing_persistent_audit_counts`
- `missing_sent_timestamp_consistency`
- `missing_duplicate_attempt_status`
- `missing_provider_anomaly_status`
- `missing_incident_state`
- `missing_reviewer_identity`
- `missing_review_timestamp`

Any completeness reason prevents complete-consistent classification.

## Consistency reasons

The ordered consistency reasons are:

- `invalid_owner_id`
- `invalid_approved_limit`
- `authorization_consumption_count_mismatch`
- `production_invocation_count_mismatch`
- `delivery_counts_mismatch`
- `delivery_attempted_event_mismatch`
- `delivery_succeeded_event_mismatch`
- `delivery_failed_event_mismatch`
- `sent_timestamp_event_mismatch`
- `sent_timestamp_inconsistent`
- `duplicate_attempt_detected`
- `audit_gap_detected`

Any consistency reason prevents complete-consistent classification.

## Privacy reasons

The privacy reasons are:

- `privacy_sanitizer_not_applied`
- `sensitive_evidence_detected`

A privacy reason produces `privacy_rejected`.

The review must not expose the rejected sensitive value in its result.

## Incident reasons

The incident reasons are:

- `provider_anomaly_detected`
- `incident_open`
- `incident_state_invalid`
- `failed_delivery_present`
- `unexpected_refusal_present`

An incident reason produces `incident_escalated`.

Escalation does not perform a retry.

## Policy reasons

The policy reasons are:

- `automatic_retry_enabled`
- `automatic_rollout_promotion_enabled`
- `production_delivery_attempted_during_review`

A policy reason makes the evidence ineligible for rollout consideration.

## Deterministic reason order

The global reason order contains exactly 38 unique reason codes.

The implementation checkpoint must preserve that order regardless of input
mapping order.

No arbitrary set ordering may be exposed.

## Reconciliation rules

Evidence review must verify:

- Authorization-consumption count equals one.
- Production-invocation count equals one.
- Delivery outcomes reconcile to the reviewed candidate count.
- Failed count equals zero for complete-consistent classification.
- Unexpected refusal count equals zero.
- `delivery_attempted` count equals delivered plus failed.
- `delivery_succeeded` count equals delivered.
- `delivery_failed` count equals failed.
- `sent_timestamp_recorded` count equals delivered.
- Sent timestamps are internally consistent.
- Duplicate-attempt review is clean.
- Persistent audit has no gaps.
- Provider anomaly is absent.
- Incident state is closed or explicitly escalated.
- Automatic retry is disabled.
- Automatic rollout promotion is disabled.

## Persistent audit evidence

Successful delivery evidence remains:

1. `delivery_attempted`
2. `delivery_succeeded`
3. `sent_timestamp_recorded`

Failed delivery evidence remains:

1. `delivery_attempted`
2. `delivery_failed`

The review may inspect sanitized event counts and states.

It may not edit or delete audit events.

## Required reviewers

The evidence-review package requires:

- Evidence reviewer
- Privacy reviewer
- Incident reviewer

Privacy rejection and incident escalation require the relevant reviewer
identity to be present in retained evidence.

## Evidence allowlist

The review allowlist may retain only:

- Change-record and authorization identifiers
- Owner and approved limit
- Authorization command fingerprint
- Freeze fingerprint
- Invocation and consumption counts
- Delivery outcome counts
- Persistent audit counts
- Sent-timestamp consistency
- Duplicate-attempt status
- Audit-gap status
- Provider-anomaly status
- Incident state
- Privacy-sanitizer state
- Automatic-retry state
- Automatic-rollout-promotion state
- Reviewer identities
- Review timestamp
- Final decision
- Rollout recommendation
- Stable reason codes
- Incident reference

Unknown fields are discarded.

## Privacy exclusions

The review excludes:

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

Sensitive evidence produces `privacy_rejected`.

The rejected value must not be copied into logs, decisions or incidents.

## Readiness and command boundary

The report-only readiness commands remain:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

and:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

The reviewed production-command shape remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

v262 executes none of these production actions.

Evidence review must not invoke the production command.

## No-repair boundary

Evidence review must not:

- Modify sent timestamps
- Delete persistent audit events
- Recreate audit events
- Change delivery counts
- Change authorization state
- Change the freeze fingerprint
- Use direct SQL repair
- Use Django shell timestamp repair
- Hide partial failure
- Reclassify an open incident as closed without evidence

Incomplete or inconsistent evidence remains incomplete or inconsistent.

## No-retry boundary

Evidence review cannot trigger:

- Blind retry
- Manual retry
- Automatic retry
- Scheduler retry
- Multi-owner retry
- Global all-owner retry

A retry requires a separate future authorization and checkpoint.

## No-automatic-promotion boundary

`complete_consistent` means only that the reviewed evidence is internally
complete and consistent.

It does not mean:

- Production delivery is safe for all owners.
- A larger pilot is authorized.
- The feature gate should be changed.
- The scheduler should be enabled.
- A rollout phase should be promoted.
- Provider risk is eliminated.

Any rollout decision remains manual and outside this checkpoint.

## Prohibited actions

The evidence-review contract prohibits:

- Production delivery during review
- Authorization consumption during review
- Delivery retry during review
- Automatic rollout promotion
- Automatic retry
- Global all-owner execution
- Multi-owner execution
- Manual sent-timestamp edits
- Manual audit-event deletion
- Direct SQL repair
- Django shell timestamp repair
- Credential logging
- Recipient-payload logging
- Saved-search-payload logging
- Rendered email-payload logging
- Provider response-body logging
- Privacy-sanitizer bypass
- Classification without required evidence
- Rollout recommendation without manual reviewer decision
- Silent inconsistency acceptance

## Runtime and schema boundary

v262 and proposed v263 introduce no changes to:

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

## v263 acceptance gate

v263 is accepted only when:

- Scope is exactly the two contracted files.
- Evidence completeness evaluation is deterministic.
- Evidence consistency evaluation is deterministic.
- Decision precedence is deterministic.
- All 38 reason codes remain reachable.
- Reason-code order remains stable.
- Privacy rejection removes sensitive values.
- Incident escalation performs no retry.
- Complete-consistent performs no rollout promotion.
- Invocation and consumption counts are reconciled.
- Delivery and audit counts are reconciled.
- Sent timestamps are reconciled.
- Duplicate-attempt and audit-gap states are evaluated.
- Evidence sanitization is allowlist based.
- Unknown fields are discarded.
- No production delivery occurs.
- No authorization is consumed.
- No retry occurs.
- Runtime, scheduler, schema and UI remain unchanged.
- Historical safety tests pass.
- Full regression passes.

## Next checkpoint

v263: saved-search notification production delivery pilot supervised execution evidence review implementation
