# v266 — Saved-Search Notification Production Delivery Pilot Supervised Execution Manual Rollout Consideration

## Checkpoint identity

- Base:
  `project-checkpoint-v265-saved-search-notification-production-delivery-pilot-supervised-execution-manual-rollout-consideration-contract`
- Target:
  `project-checkpoint-v266-saved-search-notification-production-delivery-pilot-supervised-execution-manual-rollout-consideration`
- Marker:
  `V266_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_CONSIDERATION`

## Purpose

v266 implements the v265 manual-rollout consideration contract as a pure,
deterministic and documentation-and-test-only reference implementation.

It determines only whether a human-controlled team may prepare a separate
future authorization package.

It does not authorize or perform production delivery.

## Exact v266 scope

v266 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_consideration_v266.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_consideration_v266.md`

## Proposed v267 closeout scope

v267 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_consideration_closeout_audit_v267.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_consideration_closeout_audit_v267.md`

v267 remains documentation and test only.

## Implementation boundary

All implementation functions exist only in the v266 test module.

v266 does not modify:

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
- Settings
- Migrations

## Pure reference functions

v266 provides pure functions for:

- Building a complete consideration record
- Building an evaluation context
- Detecting missing values
- Evaluating inclusive freshness
- Ordering and deduplicating reason codes
- Collecting completeness reasons
- Collecting source-eligibility reasons
- Collecting owner, limit, role and freshness reasons
- Collecting prohibited-action reasons
- Creating an immutable snapshot
- Sanitizing evidence
- Computing the final decision

No function performs an external action.

## Reference record

The complete record contains the 47 fields contracted in v265.

Default source evidence is:

- `complete_consistent`
- `eligible_for_manual_consideration`
- Complete
- Consistent
- Privacy-safe
- Incident-clear
- Policy-compliant
- Bound to one consumed source authorization
- Bound to one production invocation
- Free of failed and refused deliveries
- Gap-free
- Duplicate-clean
- Provider-anomaly-free
- Incident state closed
- Sanitized
- Automatic retry disabled
- Automatic rollout promotion disabled

## Evaluation context

Freshness information is supplied through a separate immutable evaluation
context.

The context contains:

- Current timestamp
- Readiness evidence generation timestamp
- Preview evidence generation timestamp
- Consideration start timestamp
- Expected readiness fingerprint
- Expected preview fingerprint

The context is not retained as production evidence.

## Final result

The evaluator returns:

- Decision
- Eligibility boolean
- Ordered reason codes
- Sanitized evidence
- Immutable snapshot
- Future-authorization requirements

It does not return:

- Production command
- Executable plan
- New authorization identifier
- Reused source authorization
- Provider payload
- Recipient payload
- Credentials

## Decision boundary

The only decisions remain:

- `not_eligible`
- `eligible_to_prepare_future_authorization`

Any reason code produces `not_eligible`.

Eligibility requires an empty reason-code collection.

## Eligibility meaning

`eligible_to_prepare_future_authorization` means only that a new,
human-reviewed authorization package may be prepared.

It does not:

- Execute production delivery
- Create authorization automatically
- Reuse the source authorization
- Consume authorization
- Retry delivery
- Enable the scheduler
- Enable automatic retry
- Promote rollout automatically
- Change the production feature gate

## Ordered reason package

All 48 v265 reason codes remain reachable.

The families remain:

- 14 completeness reasons
- 18 source-eligibility reasons
- 11 owner, limit, role and freshness reasons
- 5 prohibited-action reasons

Returned reason order always follows `MANUAL_ROLLOUT_REASON_ORDER`.

## Completeness evaluation

The implementation checks required presence of:

- Consideration identifier
- Source change-record identifier
- Source authorization identifier
- Source owner identifier
- Source approved limit
- Source command fingerprint
- Source freeze fingerprint
- Decision owner
- All required reviewer identities
- Considered owner scope
- Considered limit
- Readiness fingerprint
- Preview fingerprint
- Consideration completion timestamp

Missing evidence fails closed.

## Source evidence evaluation

The source must remain:

- Decision `complete_consistent`
- Recommendation `eligible_for_manual_consideration`
- Free of reason codes
- Complete
- Consistent
- Privacy-safe
- Incident-clear
- Policy-compliant
- Bound to one authorization consumption
- Bound to one production invocation

Any mismatch produces a stable reason.

## Source delivery reconciliation

The source delivery counts must:

- Be nonnegative integers
- Have a total of at least one
- Not exceed the source approved limit
- Contain zero failed deliveries
- Contain zero refused deliveries

A mismatch produces:

`source_delivery_counts_not_reconciled`

## Source audit and incident evaluation

The source must remain:

- Audit-gap-free
- Duplicate-attempt-clean
- Provider-anomaly-free
- Incident state closed
- Privacy-sanitized
- Automatic retry disabled
- Automatic rollout promotion disabled

Each violation remains independently visible.

## Owner-scope evaluation

The source owner must be a positive integer.

The considered owner scope must:

- Contain exactly one owner
- Contain the source owner
- Add no other owner

An empty scope produces:

`considered_owner_scope_empty`

A mismatched or expanded scope produces:

`considered_owner_scope_expanded`

## Limit evaluation

The source and considered limits must be integers between one and three.

The considered limit cannot exceed the source approved limit.

Invalid limits and limit expansion remain separate reasons.

The stable limit reason codes are:

- `considered_limit_invalid`
- `considered_limit_expanded`

## Role-separation evaluation

The required roles remain:

- Decision owner
- Evidence reviewer
- Privacy reviewer
- Incident reviewer
- Rollback reviewer
- Incident commander

The decision owner must differ from every reviewer and incident commander.

Evidence, privacy, incident and rollback reviewers must be pairwise distinct.

Role overlap fails closed.

## Readiness freshness

Readiness evidence remains valid when:

    0 <= current_timestamp - readiness_generated_at <= 300

The exact 300-second boundary is valid.

A future timestamp, stale timestamp or fingerprint mismatch produces:

`readiness_evidence_stale_or_changed`

## Preview freshness

Preview evidence remains valid when:

    0 <= current_timestamp - preview_generated_at <= 300

The exact 300-second boundary is valid.

A future timestamp, stale timestamp or fingerprint mismatch produces:

`preview_evidence_stale_or_changed`

## Consideration lifetime

Consideration remains valid when:

    0 <= current_timestamp - consideration_started_at <= 900

The exact 900-second boundary is valid.

An expired consideration invalidates both readiness and preview eligibility
because a new current evidence package is required.

## Future authorization requirement

Eligibility requires:

`future_authorization_required = true`

The result returns the 13 future-authorization requirements only when eligible.

It does not create the authorization package.

## Future authorization package

A future package must still contain:

1. New authorization identifier
2. One explicit positive owner identifier
3. Explicit limit between one and three
4. Current readiness evidence
5. Current preview evidence
6. Current provider, sender and backend state
7. Current command fingerprint
8. Current pre-send freeze fingerprint
9. Current operator and reviewer identities
10. Both production confirmations
11. Explicit expiration
12. One-shot consumption
13. Disabled automatic retry and automatic promotion

## Prohibited-action evaluation

The result becomes `not_eligible` when consideration reports:

- Production delivery performed
- Authorization consumed
- Retry performed
- Scheduler enabled
- Automatic promotion performed

Missing no-action flags also fail closed because they are not explicitly false.

## Decision spoofing protection

Input values for:

- `final_decision`
- `reason_codes`

cannot control the result.

The evaluator overwrites both values with computed values before sanitization.

## Strict sanitizer

The sanitizer retains only the 47-field v265 allowlist.

Unknown fields are discarded.

Sensitive fields are discarded.

Sensitive values cannot appear in the returned result.

## Privacy exclusions

The implementation continues to exclude:

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

## Immutable snapshot

The immutable snapshot retains exactly:

- Consideration identifier
- Source change-record identifier
- Source authorization identifier
- Source owner identifier
- Source approved limit
- Source command fingerprint
- Source freeze fingerprint
- Readiness fingerprint
- Preview fingerprint

Snapshot generation is deterministic and read-only.

## No-external-action proof

Tests verify that evaluation does not call:

- `subprocess.run`
- Django management commands
- Django email connection creation

Evaluation performs no database mutation.

## Production-command boundary

The guarded production-command shape remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

v266 does not execute or construct this command.

## Readiness boundary

The report-only readiness commands remain:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

and:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

A future authorization must use regenerated current readiness evidence.

## No-production-action boundary

v266 performs no:

- Production delivery
- Email rendering
- Email connection
- Provider call
- Management command invocation
- Subprocess invocation
- Database mutation

## No-authorization-consumption boundary

v266 does not:

- Consume authorization
- Reopen authorization
- Renew authorization
- Revoke authorization
- Modify authorization state
- Reuse source authorization

## No-retry boundary

v266 performs no:

- Blind retry
- Manual retry
- Automatic retry
- Scheduler retry
- Multi-owner retry
- Global all-owner retry

## No-scheduler boundary

v266 cannot:

- Enable a scheduler
- Add a periodic task
- Add cron execution
- Add startup execution
- Add a background worker
- Enable automatic delivery

## No-automatic-promotion boundary

v266 cannot:

- Promote rollout automatically
- Increase owner scope
- Increase limit
- Enable the production feature gate
- Approve a production command
- Generate authorization automatically

## No-repair boundary

v266 does not:

- Edit sent timestamps
- Delete audit events
- Recreate audit events
- Alter delivery counts
- Replace fingerprints
- Use Direct SQL repair
- Use Django shell timestamp repair
- Rewrite source evidence
- Hide inconsistency

## Runtime and schema boundary

v266 introduces no changes to:

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

## v267 closeout gate

v267 must verify:

- Exact v265 contract preservation
- Exact v266 implementation preservation
- Exact two-file closeout scope
- All 48 reason codes remain reachable
- Deterministic reason order
- Inclusive freshness boundaries
- Owner scope cannot expand
- Limit cannot expand
- Role overlap fails closed
- Source evidence mismatch fails closed
- Prohibited actions fail closed
- Eligible result permits only future-authorization preparation
- No production delivery
- No authorization consumption
- No retry
- No scheduler enablement
- No automatic promotion
- Strict sanitization
- No sensitive-value leakage
- Runtime and schema remain unchanged
- Migration 0017 remains absent
- Historical safety tests pass
- Full regression passes

## Next checkpoint

v267: saved-search notification production delivery pilot supervised execution manual rollout consideration closeout audit
