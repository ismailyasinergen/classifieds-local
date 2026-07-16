# v263 — Saved-Search Notification Production Delivery Pilot Supervised Execution Evidence Review

## Checkpoint identity

- Base:
  `project-checkpoint-v262-saved-search-notification-production-delivery-pilot-supervised-execution-evidence-review-contract`
- Target:
  `project-checkpoint-v263-saved-search-notification-production-delivery-pilot-supervised-execution-evidence-review`
- Marker:
  `V263_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_EVIDENCE_REVIEW`

## Purpose

v263 implements the v262 evidence-review contract as a deterministic,
documentation-and-test-only reference implementation.

The implementation evaluates sanitized supervised-execution evidence and
returns one deterministic classification.

It performs no production delivery, authorization consumption, retry, data
repair or rollout promotion.

## Exact v263 scope

v263 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_evidence_review_v263.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_evidence_review_v263.md`

## Proposed v264 closeout scope

v264 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_evidence_review_closeout_audit_v264.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_evidence_review_closeout_audit_v264.md`

v264 remains documentation and test only.

## Implementation boundary

All v263 implementation functions exist only in the v263 test module.

The implementation does not modify or invoke:

- Production sender
- Production command
- Readiness runtime
- Scheduler
- Matcher
- Renderer
- Audit runtime
- Audit persistence
- Models
- Admin
- URLs
- Templates
- Migrations
- Email connections
- External processes

## Reference evidence record

The reference record contains:

- Change-record identifier
- Authorization identifier
- Positive owner identifier
- Approved limit
- Authorization command fingerprint
- Freeze fingerprint
- Authorization-consumption count
- Production-invocation count
- Delivery outcome counts
- Persistent audit-event counts
- Sent-timestamp consistency
- Duplicate-attempt status
- Audit-gap status
- Provider-anomaly status
- Incident state
- Privacy-sanitizer status
- Automatic-retry status
- Automatic-rollout-promotion status
- Reviewer identities
- Review timestamp
- Computed decision
- Computed rollout recommendation
- Computed reason codes
- Optional incident reference

The default reference record is complete and consistent.

## Pure implementation functions

v263 provides pure reference functions for:

- Building complete evidence
- Detecting missing evidence
- Collecting completeness reasons
- Collecting consistency reasons
- Collecting privacy reasons
- Collecting incident reasons
- Collecting policy reasons
- Ordering and deduplicating reason codes
- Building immutable evidence snapshots
- Sanitizing evidence
- Evaluating the final review decision

None of these functions performs an external action.

## Completeness evaluation

Completeness evaluation checks:

- Change-record identifier
- Authorization identifier
- Owner identifier
- Approved limit
- Authorization command fingerprint
- Freeze fingerprint
- Authorization-consumption count
- Production-invocation count
- All delivery outcome counts
- All persistent audit-event counts
- Sent-timestamp consistency
- Duplicate-attempt status
- Provider-anomaly status
- Incident state
- Reviewer identity
- Review timestamp

Missing grouped counts produce one stable grouped reason.

## Consistency evaluation

Consistency evaluation requires:

- Positive integer owner identifier
- Approved limit between one and three
- Authorization-consumption count equal to one
- Production-invocation count equal to one
- Nonnegative integer delivery counts
- At least one reviewed outcome
- Total outcomes no greater than the approved limit
- Attempted audit count equal to delivered plus failed
- Succeeded audit count equal to delivered
- Failed audit count equal to failed
- Sent-timestamp audit count equal to delivered
- Internally consistent sent timestamps
- Clean duplicate-attempt review
- Gap-free persistent audit

Any mismatch produces an inconsistent result unless a higher-precedence
privacy or incident classification applies.

## Deterministic decision precedence

Decision precedence remains:

1. `privacy_rejected`
2. `incident_escalated`
3. `incomplete`
4. `inconsistent`
5. `not_eligible_for_rollout_consideration`
6. `complete_consistent`

The same input always produces the same decision and reason order.

## Complete-consistent result

A complete-consistent result means:

- Required evidence is present.
- Counts and audit evidence reconcile.
- Privacy controls passed.
- No incident reason is active.
- No prohibited policy state is active.

It permits only:

`eligible_for_manual_consideration`

It does not authorize:

- Another production delivery
- A larger owner scope
- A larger pilot limit
- Scheduler enablement
- Automatic retry
- Automatic rollout promotion

## Privacy rejection

Privacy rejection occurs when:

- The privacy sanitizer was not applied.
- Sensitive evidence keys are present.

Sensitive inputs include:

- SMTP password
- SMTP username
- API key
- Access token
- Recipient email
- Default sender
- Raw email-backend value
- Saved-search name
- Saved-search querystring
- Rendered subject
- Rendered body
- Provider response body
- Raw exception traceback

Sensitive keys and values are excluded from the result.

## Incident escalation

Incident escalation occurs when:

- Provider anomaly is present.
- Incident state is open.
- Incident state is invalid.
- Failed delivery is present.
- Unexpected refusal is present.

Escalation:

- Performs no retry
- Consumes no authorization
- Changes no timestamp
- Deletes no audit event
- Executes no production command

## Policy ineligibility

The evidence becomes
`not_eligible_for_rollout_consideration` when:

- Automatic retry is enabled.
- Automatic rollout promotion is enabled.
- Production delivery was attempted during evidence review.

Policy ineligibility produces rollout recommendation:

`not_eligible`

## Immutable snapshot

The immutable snapshot contains exactly:

- Change-record identifier
- Authorization identifier
- Owner identifier
- Approved limit
- Authorization command fingerprint
- Freeze fingerprint

The snapshot is deterministic and read-only.

## Strict evidence sanitizer

The sanitizer retains only the v262 evidence-review allowlist.

Unknown fields are discarded.

Input values for:

- `final_decision`
- `rollout_recommendation`
- `reason_codes`

cannot spoof the computed output.

The evaluator overwrites them with computed values before sanitization.

## Stable reason package

All 38 v262 reason codes remain reachable.

The result orders reasons according to
`EVIDENCE_REVIEW_REASON_ORDER`.

Input mapping order and set ordering cannot change the returned order.

## Delivery-count reconciliation

Delivery outcomes are:

- Delivered
- Skipped
- Refused
- Failed

Every count must be a nonnegative integer.

The total must:

- Be at least one
- Not exceed the approved limit of one through three

Any violation produces:

`delivery_counts_mismatch`

## Persistent audit reconciliation

The implementation verifies:

- `delivery_attempted` equals delivered plus failed.
- `delivery_succeeded` equals delivered.
- `delivery_failed` equals failed.
- `sent_timestamp_recorded` equals delivered.

Mismatch reasons remain separate and deterministic.

## Sent-timestamp and duplicate safety

Complete-consistent requires:

- Sent timestamps internally consistent
- Duplicate-attempt review clean
- Persistent audit gap-free

Failures produce:

- `sent_timestamp_inconsistent`
- `duplicate_attempt_detected`
- `audit_gap_detected`

## Reviewer evidence

The v262 reviewer roles remain:

- Evidence reviewer
- Privacy reviewer
- Incident reviewer

Reviewer identities may be retained only through the evidence allowlist.

## Readiness and command boundary

The report-only readiness commands remain:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

and:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

The guarded production-command shape remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

v263 does not execute the production command.

## No-production-action proof

The implementation tests patch and verify that review evaluation does not call:

- `subprocess.run`
- Django email connection creation
- Django management commands

Review evaluation remains a pure in-memory classification.

## No-authorization-consumption boundary

Evidence review reads only recorded consumption count.

It does not:

- Consume authorization
- Reopen authorization
- Renew authorization
- Revoke authorization
- Change authorization state

A consumption count other than one produces:

`authorization_consumption_count_mismatch`

## No-retry boundary

Evidence review performs no:

- Blind retry
- Manual retry
- Automatic retry
- Scheduler retry
- Multi-owner retry
- Global all-owner retry

A future retry requires separate authorization and a separate checkpoint.

## No-repair boundary

Evidence review does not:

- Edit sent timestamps
- Delete audit events
- Recreate audit events
- Alter delivery counts
- Change immutable fingerprints
- Use direct SQL repair
- Use Django shell timestamp repair
- Hide partial failure

## Prohibited actions

The implementation continues to prohibit:

- Production delivery during evidence review
- Authorization consumption during evidence review
- Delivery retry during evidence review
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

v263 introduces no changes to:

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

v263 is complete only when:

- Scope is exactly two files.
- v262 remains unchanged.
- All 38 reason codes are reachable.
- Reason ordering is deterministic.
- Decision precedence is deterministic.
- Complete-consistent permits manual consideration only.
- Sensitive evidence is rejected and removed.
- Provider anomalies and open incidents escalate.
- Failed delivery and unexpected refusal escalate.
- Missing evidence is incomplete.
- Mismatched evidence is inconsistent.
- Automatic retry is ineligible.
- Automatic rollout promotion is ineligible.
- Review-time delivery attempts are ineligible.
- Unknown fields are discarded.
- Input decisions cannot spoof output.
- No production command is invoked.
- No authorization is consumed.
- No retry occurs.
- Runtime and schema remain unchanged.
- Historical safety tests pass.
- Full regression passes.
- Working tree is clean.
- The v263 tag resolves to final HEAD.

## Next checkpoint

v264: saved-search notification production delivery pilot supervised execution evidence review closeout audit
