# v264 — Saved-Search Notification Production Delivery Pilot Supervised Execution Evidence Review Closeout Audit

## Checkpoint identity

- Base:
  `project-checkpoint-v263-saved-search-notification-production-delivery-pilot-supervised-execution-evidence-review`
- Target:
  `project-checkpoint-v264-saved-search-notification-production-delivery-pilot-supervised-execution-evidence-review-closeout-audit`
- Marker:
  `V264_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_EVIDENCE_REVIEW_CLOSEOUT_AUDIT`

## Purpose

v264 closes the saved-search notification supervised-execution
evidence-review lane.

The closeout verifies that the v262 contract and v263 deterministic reference
implementation remain internally complete, fail closed, privacy-safe and
strictly nonexecuting.

This checkpoint performs no production delivery.

## Exact v264 scope

v264 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_evidence_review_closeout_audit_v264.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_evidence_review_closeout_audit_v264.md`

## Closed evidence-review package

The closed evidence-review package consists of:

- v262: evidence-review contract
- v263: deterministic reference implementation
- v264: closeout audit

Each checkpoint remains exactly two files.

No production runtime file belongs to this package.

## Proposed v265 manual-rollout consideration scope

v265 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_consideration_contract_v265.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_consideration_contract_v265.md`

v265 remains documentation and test only.

It must not perform production delivery, authorization consumption, retry,
scheduler enablement or rollout promotion.

## Required evidence closeout

The v262 package continues to require exactly 28 evidence fields covering:

- Change-record identity
- Authorization identity
- Owner and approved limit
- Authorization command fingerprint
- Freeze fingerprint
- Authorization-consumption count
- Production-invocation count
- Delivery outcome counts
- Persistent audit counts
- Sent-timestamp consistency
- Duplicate-attempt status
- Audit-gap status
- Provider-anomaly status
- Incident state
- Privacy-sanitizer state
- Retry and promotion states
- Reviewer identity
- Review timestamp
- Computed decision
- Computed reason codes

Missing required evidence cannot produce `complete_consistent`.

## Decision closeout

The six decision classifications remain:

- `privacy_rejected`
- `incident_escalated`
- `incomplete`
- `inconsistent`
- `not_eligible_for_rollout_consideration`
- `complete_consistent`

Decision precedence remains:

1. `privacy_rejected`
2. `incident_escalated`
3. `incomplete`
4. `inconsistent`
5. `not_eligible_for_rollout_consideration`
6. `complete_consistent`

The same evidence always produces the same decision.

## Complete-consistent boundary

`complete_consistent` means only that the reviewed evidence is:

- Complete
- Internally consistent
- Privacy-safe
- Incident-clear
- Policy-compliant

Its only permitted rollout recommendation is:

`eligible_for_manual_consideration`

It does not authorize:

- Production delivery
- Another command invocation
- Authorization consumption
- Authorization renewal
- Retry
- Scheduler enablement
- Owner-scope expansion
- Limit expansion
- Automatic rollout promotion

## Rollout recommendation closeout

The only recommendation values remain:

- `not_eligible`
- `eligible_for_manual_consideration`

Manual consideration is not an execution authorization.

A separate future authorization remains mandatory before any later production
activity.

## Stable reason package

All 38 unique reason codes remain packaged and reachable.

The reason families remain:

- 16 completeness reasons
- 12 consistency reasons
- 2 privacy reasons
- 5 incident reasons
- 3 policy reasons

The global order remains deterministic.

## Completeness closeout

Completeness evaluation continues to require:

- Change-record identifier
- Authorization identifier
- Positive owner identifier
- Approved limit
- Authorization command fingerprint
- Freeze fingerprint
- Known authorization-consumption count
- Known production-invocation count
- Complete delivery outcome counts
- Complete persistent audit counts
- Known sent-timestamp consistency
- Known duplicate-attempt status
- Known provider-anomaly status
- Known incident state
- Reviewer identity
- Review timestamp

Grouped missing counts retain grouped reason codes.

## Consistency closeout

Consistency evaluation continues to require:

- Positive integer owner identifier
- Approved limit between one and three
- Authorization-consumption count equal to one
- Production-invocation count equal to one
- Nonnegative integer delivery counts
- At least one reviewed outcome
- Outcome total no greater than the approved limit
- Reconciled persistent audit counts
- Consistent sent timestamps
- Clean duplicate-attempt review
- Gap-free persistent audit

Any mismatch remains fail closed.

## Delivery-count reconciliation

Reviewed outcome counts remain:

- Delivered
- Skipped
- Refused
- Failed

The total must be at least one and no greater than the approved limit of
one through three.

An invalid total returns:

`delivery_counts_mismatch`

## Persistent audit reconciliation

Persistent audit counts must satisfy:

- `delivery_attempted` equals delivered plus failed.
- `delivery_succeeded` equals delivered.
- `delivery_failed` equals failed.
- `sent_timestamp_recorded` equals delivered.

Each mismatch retains a separate stable reason code.

## Sent-timestamp and duplicate safety

Complete-consistent evidence requires:

- Sent timestamps internally consistent
- Duplicate-attempt review clean
- Persistent audit free of gaps

Violations return:

- `sent_timestamp_inconsistent`
- `duplicate_attempt_detected`
- `audit_gap_detected`

## Privacy closeout

Privacy rejection remains the highest-precedence decision.

It occurs when:

- Privacy sanitizer was not applied.
- A sensitive evidence key is present.

Sensitive values are never copied into the returned review result.

## Sensitive evidence exclusions

The closed package excludes:

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

## Strict sanitizer closeout

The sanitizer remains strict allowlist based.

Unknown fields are discarded.

Input values for:

- `final_decision`
- `rollout_recommendation`
- `reason_codes`

cannot spoof the computed output.

## Incident escalation closeout

Incident escalation remains mandatory for:

- Provider anomaly
- Open incident
- Invalid incident state
- Failed delivery
- Unexpected refusal

Escalation performs no retry and no production command.

## Policy ineligibility closeout

The result remains
`not_eligible_for_rollout_consideration` when:

- Automatic retry is enabled.
- Automatic rollout promotion is enabled.
- Production delivery is attempted during evidence review.

Policy ineligibility cannot be converted into eligibility by input fields.

## Immutable evidence snapshot

The immutable snapshot remains exactly:

- Change-record identifier
- Authorization identifier
- Pilot owner identifier
- Approved limit
- Authorization command fingerprint
- Freeze fingerprint

The snapshot is deterministic and read-only.

## No-external-action proof

The v263 evaluator remains pure and in-memory.

Tests verify it does not call:

- `subprocess.run`
- Django management commands
- Django email connection creation

It also performs no database mutation.

## Readiness and command boundary

The report-only readiness commands remain:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

and:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

The guarded production-command shape remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

v264 does not execute the production command.

## Manual rollout consideration preconditions

A future manual-rollout consideration contract must require:

- Closed evidence-review lane
- Documentation-and-test-only scope
- Decision `complete_consistent`
- Recommendation `eligible_for_manual_consideration`
- Empty reason-code collection
- Complete, consistent, privacy-safe, incident-clear and policy-compliant flags
- One change-record identifier
- One authorization identifier
- One positive owner identifier
- Approved limit between one and three
- Authorization-consumption count equal to one
- Production-invocation count equal to one
- Reconciled delivery outcomes
- Reconciled persistent audit
- Consistent sent timestamps
- Clean duplicate-attempt review
- Gap-free persistent audit
- No provider anomaly
- Closed incident state
- Applied privacy sanitizer
- Disabled automatic retry
- Disabled automatic rollout promotion
- Manual rollout decision owner
- Evidence, privacy and incident reviewers
- Rollback reviewer
- Incident commander
- Required reviewer separation
- Separate future authorization
- No production action during consideration

## Manual consideration decision boundary

Manual consideration may conclude only:

- Not eligible
- Eligible to prepare a separate future authorization package

It may not directly:

- Deliver email
- Consume authorization
- Renew authorization
- Retry delivery
- Increase the current limit
- Add owners
- Enable background delivery
- Change the production feature gate
- Promote rollout automatically

## Separate authorization boundary

Any future production action requires a new authorization package bound to:

- Explicit owner scope
- Explicit limit
- Current readiness evidence
- Current preview evidence
- Current provider and sender state
- Current reviewers
- Current command fingerprint
- Current freeze fingerprint
- Both production confirmations

The completed evidence review cannot be reused as execution authorization.

## No-retry boundary

The closed evidence-review lane performs no:

- Blind retry
- Manual retry
- Automatic retry
- Scheduler retry
- Multi-owner retry
- Global all-owner retry

Any retry requires a new authorization and a new checkpoint.

## No-repair boundary

Evidence review does not:

- Edit sent timestamps
- Delete audit events
- Recreate audit events
- Modify delivery counts
- Replace immutable fingerprints
- Use direct SQL repair
- Use Django shell timestamp repair
- Hide partial failure

## Prohibited actions

The closed lane continues to prohibit:

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

v264 introduces no changes to:

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

- Exact clean v263 base verification
- Exact v263 two-file commit-scope verification
- v263 implementation and next-lane verification
- Host-side AST validation
- Python compilation
- Django system checks
- Migration dry-run
- Applied migration verification
- Category-seed verification
- Docker Compose validation
- Readiness human and JSON smoke tests
- Production-command help smoke test
- Focused v264 closeout tests
- v262-v264 evidence-review transition tests
- v259-v264 supervision and evidence-review guard
- Historical delivery, readiness, rollback and audit safety guard
- Complete Django regression
- Protected-file checksum verification
- Exact two-file commit-scope verification

## Closeout result

The evidence-review lane is closed only when:

- v262 remains unchanged.
- v263 remains unchanged.
- v264 contains exactly two files.
- All 38 reason codes remain reachable.
- Reason ordering remains deterministic.
- Decision precedence remains deterministic.
- Count and audit reconciliation remain exact.
- Privacy rejection removes sensitive evidence.
- Incident conditions escalate.
- Policy violations remain ineligible.
- Complete-consistent remains manual-consideration only.
- Evaluator performs no external action.
- Runtime, scheduler, schema and UI remain unchanged.
- Migration 0017 remains absent.
- Full regression passes.
- The v264 tag resolves to final HEAD.
- The v264 parent remains tagged v263.
- Working tree is clean.
- No production delivery occurs.
- No remote push occurs.

## Next checkpoint

v265: saved-search notification production delivery pilot supervised execution manual rollout consideration contract
