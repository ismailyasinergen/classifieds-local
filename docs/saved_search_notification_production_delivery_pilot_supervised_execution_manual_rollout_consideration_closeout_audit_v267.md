# v267 — Saved-Search Notification Production Delivery Pilot Supervised Execution Manual Rollout Consideration Closeout Audit

## Checkpoint identity

- Base:
  `project-checkpoint-v266-saved-search-notification-production-delivery-pilot-supervised-execution-manual-rollout-consideration`
- Target:
  `project-checkpoint-v267-saved-search-notification-production-delivery-pilot-supervised-execution-manual-rollout-consideration-closeout-audit`
- Marker:
  `V267_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_CONSIDERATION_CLOSEOUT_AUDIT`

## Purpose

v267 closes the v265–v266 manual-rollout consideration lane.

The closeout verifies that the consideration implementation remains pure,
deterministic, bounded, privacy-safe and nonexecuting.

An eligible consideration result permits only preparation of a separate,
newly reviewed future authorization package.

It does not authorize production delivery.

## Exact v267 scope

v267 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_consideration_closeout_audit_v267.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_consideration_closeout_audit_v267.md`

## Proposed v268 contract scope

v268 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_authorization_contract_v268.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_authorization_contract_v268.md`

v268 remains documentation and test only.

## Closed lane

The following sequence is closed:

1. v265 manual-rollout consideration contract
2. v266 manual-rollout consideration implementation
3. v267 manual-rollout consideration closeout audit

The lane performs no production action.

## Preserved implementation result

The v266 evaluator returns exactly:

- Decision
- Eligibility boolean
- Ordered reason codes
- Sanitized evidence
- Immutable snapshot
- Future-authorization requirements

It returns no:

- Production command
- Executable plan
- Authorization identifier
- Reused source authorization
- Provider payload
- Recipient payload
- Credential

## Final decisions

The only decisions remain:

- `not_eligible`
- `eligible_to_prepare_future_authorization`

Any reason code produces `not_eligible`.

`not_eligible` retains fail-closed precedence.

## Eligibility boundary

`eligible_to_prepare_future_authorization` permits only preparation of a new
authorization contract.

It does not:

- Execute production delivery
- Consume authorization
- Reopen authorization
- Renew authorization
- Reuse the source authorization
- Retry delivery
- Enable a scheduler
- Enable automatic retry
- Promote rollout automatically
- Change the production feature gate

## Required fields

The v265 package retains exactly 47 unique required fields.

They cover:

- Source identity and immutable bindings
- Source evidence state
- Source authorization and invocation counts
- Source delivery and audit reconciliation
- Source privacy, incident and policy state
- Decision owner and required reviewers
- Considered owner scope and limit
- Readiness and preview evidence
- Computed decision and reasons
- Explicit no-action flags

Missing evidence fails closed.

## Ordered reason codes

The closeout preserves all 48 unique reason codes:

- 14 completeness reasons
- 18 source-eligibility reasons
- 11 owner, limit, role and freshness reasons
- 5 prohibited-action reasons

All 48 reasons remain reachable.

Returned ordering remains deterministic.

## Source-evidence boundary

Eligibility requires:

- `source_evidence_decision = complete_consistent`
- `source_rollout_recommendation = eligible_for_manual_consideration`
- Empty source reason-code collection
- Complete source evidence
- Consistent source evidence
- Privacy-safe source evidence
- Incident-clear source evidence
- Policy-compliant source evidence

Any mismatch fails closed.

## Authorization and invocation boundary

The historical source evidence must show:

- Exactly one source authorization consumption
- Exactly one source production invocation

These counts are evidence only.

The closeout does not consume or reuse authorization.

## Delivery reconciliation

Source delivery counts must:

- Be nonnegative integers
- Total at least one
- Not exceed the source approved limit
- Contain zero refused deliveries
- Contain zero failed deliveries

Any mismatch produces:

`source_delivery_counts_not_reconciled`

## Audit and incident boundary

The source must remain:

- Audit-gap-free
- Duplicate-attempt-clean
- Provider-anomaly-free
- Incident state closed
- Privacy-sanitized
- Automatic retry disabled
- Automatic rollout promotion disabled

Every violation remains independently visible.

## Owner-scope boundary

The source owner must be a positive integer.

The considered owner scope must:

- Contain exactly one owner
- Contain the source owner
- Add no other owner
- Never use a global all-owner scope

Expansion produces:

`considered_owner_scope_expanded`

## Limit boundary

The source and considered limits must be integers from one through three.

The considered limit cannot exceed the source approved limit.

The stable limit reasons remain:

- `considered_limit_invalid`
- `considered_limit_expanded`

## Role boundary

The required roles remain:

- Decision owner
- Evidence reviewer
- Privacy reviewer
- Incident reviewer
- Rollback reviewer
- Incident commander

The decision owner remains distinct from all reviewer and incident-command
roles.

Evidence, privacy, incident and rollback reviewers remain pairwise distinct.

## Readiness freshness boundary

Readiness evidence is current only when:

    0 <= current_timestamp - readiness_generated_at <= 300

The exact 300-second boundary remains valid.

Stale, future-dated or fingerprint-mismatched evidence produces:

`readiness_evidence_stale_or_changed`

## Preview freshness boundary

Preview evidence is current only when:

    0 <= current_timestamp - preview_generated_at <= 300

The exact 300-second boundary remains valid.

Stale, future-dated or fingerprint-mismatched evidence produces:

`preview_evidence_stale_or_changed`

## Consideration lifetime boundary

Consideration remains current only when:

    0 <= current_timestamp - consideration_started_at <= 900

The exact 900-second boundary remains valid.

An expired consideration requires regenerated readiness and preview evidence.

## Future authorization boundary

A positive closeout result still requires a separate future authorization.

The future authorization must include:

1. New authorization identifier
2. One explicit positive owner identifier
3. Explicit limit between one and three
4. Regenerated readiness evidence
5. Regenerated preview evidence
6. Current provider, sender and backend state
7. Current command fingerprint
8. Current pre-send freeze fingerprint
9. Current operator and reviewer identities
10. Both production confirmations
11. Explicit authorization expiration
12. One-shot authorization consumption
13. Disabled automatic retry and automatic promotion

The source authorization is historical evidence only.

## Manual-rollout authorization preconditions

v267 packages 47 preconditions for v268.

They require:

- Closed consideration lane
- Eligible source decision
- Empty reason-code collection
- Sanitized evidence
- Complete immutable snapshot
- Positive one-owner scope
- Limit bounded from one through three
- Regenerated readiness and preview evidence
- Regenerated provider, command and freeze state
- Complete and separated role identities
- New expiring authorization
- One-shot consumption
- Both production confirmations
- Disabled retry, scheduler and automatic promotion
- No production delivery during closeout
- No authorization consumption during closeout
- No retry during closeout
- Unchanged runtime and schema
- Green historical and full regression tests

## Prohibited-action boundary

The result becomes `not_eligible` when consideration reports:

- Production delivery performed
- Authorization consumed
- Retry performed
- Scheduler enabled
- Automatic promotion performed

Missing no-action flags also fail closed.

## Decision spoofing boundary

Input values for:

- `final_decision`
- `reason_codes`

cannot control the result.

The evaluator overwrites them with computed values.

## Strict sanitizer boundary

Only the 47-field evidence allowlist may be retained.

Unknown fields are discarded.

Sensitive fields are discarded.

Sensitive values must not appear in results.

## Privacy exclusions

The closed lane excludes:

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

## Immutable snapshot boundary

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

Snapshot generation remains deterministic and read-only.

## No-external-action proof

The closeout verifies that evaluation does not call:

- `subprocess.run`
- Django management commands
- Django email connection creation

It performs no database mutation.

## Production-command boundary

The guarded production-command shape remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

v267 does not execute or construct this command.

## Readiness boundary

The report-only readiness commands remain:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

and:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

Any future authorization must use regenerated current readiness evidence.

## No-production-action boundary

v267 performs no:

- Production delivery
- Email rendering
- Email connection
- Provider call
- Management command invocation
- Subprocess invocation
- Database mutation

## No-authorization-consumption boundary

v267 does not:

- Consume authorization
- Reopen authorization
- Renew authorization
- Revoke authorization
- Modify authorization state
- Reuse source authorization

## No-retry boundary

v267 performs no:

- Blind retry
- Manual retry
- Automatic retry
- Scheduler retry
- Multi-owner retry
- Global all-owner retry

## No-scheduler boundary

v267 cannot:

- Enable a scheduler
- Add a periodic task
- Add cron execution
- Add startup execution
- Add a background worker
- Enable automatic delivery

## No-automatic-promotion boundary

v267 cannot:

- Promote rollout automatically
- Increase owner scope
- Increase limit
- Enable the production feature gate
- Approve a production command
- Generate authorization automatically

## No-repair boundary

v267 does not:

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

v267 introduces no changes to:

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

## v268 acceptance boundary

v268 may define only a manual-rollout authorization contract.

It must remain documentation and test only.

It must require:

- A new authorization identifier
- Positive one-owner scope
- Explicit limit from one through three
- Regenerated readiness and preview evidence
- Current provider, sender and backend state
- Current command and freeze fingerprints
- Separated operator and reviewer roles
- Both production confirmations
- Explicit expiration
- One-shot consumption
- Disabled retry, scheduler and automatic promotion

v268 must perform no production delivery.

## Closeout result

The manual-rollout consideration lane is closed.

A successful consideration result means only:

`eligible_to_prepare_future_authorization`

It is not production authorization.

## Next checkpoint

v268: saved-search notification production delivery pilot supervised execution manual rollout authorization contract
