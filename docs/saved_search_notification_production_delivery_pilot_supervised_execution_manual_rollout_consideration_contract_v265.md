# v265 — Saved-Search Notification Production Delivery Pilot Supervised Execution Manual Rollout Consideration Contract

## Checkpoint identity

- Base:
  `project-checkpoint-v264-saved-search-notification-production-delivery-pilot-supervised-execution-evidence-review-closeout-audit`
- Target:
  `project-checkpoint-v265-saved-search-notification-production-delivery-pilot-supervised-execution-manual-rollout-consideration-contract`
- Marker:
  `V265_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_CONSIDERATION_CONTRACT`

## Purpose

v265 defines a documentation-and-test-only contract for manually considering
whether a completed supervised-execution pilot may proceed to preparation of a
separate future authorization package.

Manual consideration is not production authorization.

This checkpoint performs no:

- Production delivery
- Authorization consumption
- Retry
- Scheduler enablement
- Feature-gate mutation
- Automatic rollout promotion

## Exact v265 scope

v265 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_consideration_contract_v265.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_consideration_contract_v265.md`

## Proposed v266 implementation scope

v266 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_consideration_v266.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_consideration_v266.md`

v266 remains documentation and test only.

It must not modify production runtime, schema, scheduler or UI.

## Closed evidence-review dependency

Manual rollout consideration requires the closed v262–v264 evidence-review
package.

The source evidence must have:

- Decision `complete_consistent`
- Recommendation `eligible_for_manual_consideration`
- Empty reason-code collection
- Complete flag true
- Consistent flag true
- Privacy-safe flag true
- Incident-clear flag true
- Policy-compliant flag true

Any different source result is not eligible.

## Required consideration fields

The contract requires exactly 47 fields covering:

- Consideration identity
- Source change-record identity
- Source authorization identity
- Source owner and approved limit
- Source command and freeze fingerprints
- Source evidence decision and recommendation
- Source evidence flags and reason codes
- Source invocation and consumption counts
- Source delivery outcome counts
- Source duplicate, audit, anomaly and incident state
- Source privacy, retry and promotion state
- Decision owner
- Evidence, privacy, incident and rollback reviewers
- Incident commander
- Considered owner scope and limit
- Current readiness fingerprint
- Current preview fingerprint
- Consideration completion time
- Computed decision and reasons
- Future-authorization requirement
- Explicit no-action state fields

Missing required fields make the consideration `not_eligible`.

## Final decisions

The only final decisions are:

- `not_eligible`
- `eligible_to_prepare_future_authorization`

`not_eligible` has fail-closed precedence.

Eligibility never means production delivery is authorized.

## Eligibility meaning

`eligible_to_prepare_future_authorization` means only that a human-controlled
future authorization package may be prepared.

It does not permit:

- Running the production command
- Reusing the source authorization
- Consuming authorization
- Retrying delivery
- Adding owners
- Increasing the approved limit
- Enabling the scheduler
- Enabling automatic retry
- Promoting rollout automatically

## Source evidence requirements

The source evidence must remain:

- `complete_consistent`
- `eligible_for_manual_consideration`
- Free of reason codes
- Complete and internally consistent
- Privacy-safe
- Incident-clear
- Policy-compliant
- Bound to one consumed authorization
- Bound to one production invocation
- Reconciled across delivery counts and persistent audit
- Free of duplicate attempts
- Free of audit gaps
- Free of provider anomaly
- Bound to a closed incident state
- Sanitized
- Free of automatic retry
- Free of automatic rollout promotion

## Immutable bindings

The following values remain immutable during consideration:

- Consideration identifier
- Source change-record identifier
- Source authorization identifier
- Source owner identifier
- Source approved limit
- Source authorization command fingerprint
- Source freeze fingerprint
- Current readiness-evidence fingerprint
- Current preview-evidence fingerprint

A mismatch makes the result `not_eligible`.

## Owner-scope boundary

Manual consideration supports exactly one owner.

The considered owner scope must:

- Contain one positive owner identifier
- Match the source owner
- Never add another owner
- Never use a global all-owner scope

Multi-owner or expanded scope is not eligible.

## Limit boundary

The considered limit must:

- Be an integer
- Be between one and three
- Not exceed the source approved limit

Manual consideration cannot increase the pilot limit.

## Freshness boundary

The contract defines:

- Readiness evidence freshness: 300 seconds
- Preview evidence freshness: 300 seconds
- Consideration lifetime: 900 seconds

Stale or changed readiness and preview evidence make the result not eligible.

Freshness evaluation must be inclusive at the exact boundary.

## Required roles

The manual consideration package requires:

- Decision owner
- Evidence reviewer
- Privacy reviewer
- Incident reviewer
- Rollback reviewer
- Incident commander

Missing role identities make the result not eligible.

## Role separation

The decision owner must differ from:

- Evidence reviewer
- Privacy reviewer
- Incident reviewer
- Rollback reviewer
- Incident commander

Evidence, privacy, incident and rollback reviewers must be pairwise distinct.

Role overlap fails closed.

## Ordered reason codes

The contract defines 48 unique ordered reason codes:

- 14 completeness reasons
- 18 source-evidence eligibility reasons
- 11 scope, freshness and role reasons
- 5 prohibited-action reasons

Reason ordering is deterministic.

Input mapping or set ordering must not alter output order.

## Completeness reasons

The completeness reasons cover missing:

- Consideration identity
- Source change-record identity
- Source authorization identity
- Source owner
- Source approved limit
- Source command fingerprint
- Source freeze fingerprint
- Decision owner
- Required reviewer identity
- Considered owner scope
- Considered limit
- Readiness fingerprint
- Preview fingerprint
- Consideration timestamp

Any missing item makes the result not eligible.

## Source-eligibility reasons

The source evidence is rejected when:

- Decision is not `complete_consistent`
- Recommendation is not `eligible_for_manual_consideration`
- Reason codes are nonempty
- Complete flag is false
- Consistent flag is false
- Privacy-safe flag is false
- Incident-clear flag is false
- Policy-compliant flag is false
- Authorization-consumption count is not one
- Production-invocation count is not one
- Delivery counts do not reconcile
- Persistent audit contains gaps
- Duplicate-attempt review is not clean
- Provider anomaly is present
- Incident state is not closed
- Privacy sanitizer was not applied
- Automatic retry is enabled
- Automatic rollout promotion is enabled

## Scope, freshness and role reasons

The contract rejects:

- Invalid source owner
- Invalid source approved limit
- Empty considered owner scope
- Expanded considered owner scope
- Invalid considered limit
- Expanded considered limit
- Decision-owner role overlap
- Required reviewer overlap
- Stale or changed readiness evidence
- Stale or changed preview evidence
- Missing future-authorization requirement

## Prohibited-action reasons

The result becomes not eligible if consideration reports:

- Production delivery performed
- Authorization consumed
- Retry performed
- Scheduler enabled
- Automatic promotion performed

The consideration step must remain completely nonexecuting.

## Strict evidence allowlist

Only the 47 required contract fields may be retained.

Unknown fields are discarded.

The allowlist excludes:

- Credentials
- Recipient identity
- Sender configuration
- Email backend path
- Saved-search payload
- Rendered subject
- Rendered body
- Provider response body
- Raw traceback

## Privacy exclusions

The contract excludes:

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

Sensitive values must never appear in retained evidence or decision output.

## Future authorization boundary

Any future production action requires a new authorization package.

The future package must include:

1. New authorization identifier
2. One explicit positive owner identifier
3. Explicit limit between one and three
4. Current readiness evidence
5. Current preview evidence
6. Current provider, sender and backend state
7. Current authorization command fingerprint
8. Current pre-send freeze fingerprint
9. Current operator and reviewer identities
10. Both production confirmations
11. Explicit authorization expiration
12. One-shot authorization consumption
13. Disabled automatic retry and automatic promotion

The source authorization cannot be renewed or reused.

## Production-command boundary

The guarded production-command shape remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

v265 does not execute this command.

The contract does not create an executable command plan.

## Readiness boundary

The report-only readiness commands remain:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

and:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

Readiness evidence must be regenerated for any future authorization.

The old evidence-review result cannot substitute for current readiness.

## No-production-action boundary

Manual consideration performs no:

- Production delivery
- Email rendering
- Email connection
- Provider call
- Management command invocation
- Subprocess invocation
- Database mutation

It is a deterministic in-memory decision process only.

## No-authorization-consumption boundary

Manual consideration:

- Does not consume authorization
- Does not reopen authorization
- Does not renew authorization
- Does not revoke authorization
- Does not modify authorization state

The source authorization is historical evidence only.

## No-retry boundary

Manual consideration performs no:

- Blind retry
- Manual retry
- Automatic retry
- Scheduler retry
- Multi-owner retry
- Global all-owner retry

Any future retry requires its own authorization and checkpoint.

## No-scheduler boundary

Manual consideration cannot:

- Enable a scheduler
- Add a periodic task
- Add cron execution
- Add startup execution
- Add a background worker
- Enable automatic delivery

The scheduler remains nonautomatic.

## No-automatic-promotion boundary

Manual consideration cannot:

- Promote rollout automatically
- Increase owner scope automatically
- Increase limit automatically
- Enable the production feature gate
- Approve a production command
- Generate an authorization automatically

Only a separate reviewed future authorization can permit later activity.

## No-repair boundary

Manual consideration does not:

- Edit sent timestamps
- Delete audit events
- Recreate audit events
- Alter delivery counts
- Replace fingerprints
- Use direct SQL repair
- Use Django shell timestamp repair
- Hide an inconsistency
- Rewrite source evidence

Invalid source evidence remains invalid.

## Prohibited actions

The contract prohibits:

- Production delivery during consideration
- Authorization consumption during consideration
- Delivery retry during consideration
- Scheduler enablement
- Automatic rollout promotion
- Production feature-gate mutation
- Owner-scope expansion
- Limit expansion
- Source authorization reuse
- Evidence review reused as execution authorization
- Global all-owner execution
- Multi-owner execution
- Blind retry
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
- Computed-decision spoofing
- Silent inconsistency acceptance

## Runtime and schema boundary

v265 and proposed v266 introduce no changes to:

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

## v266 acceptance gate

v266 is accepted only when:

- Scope is exactly the two contracted files.
- Manual consideration remains pure and in-memory.
- All 48 reason codes are reachable.
- Reason ordering is deterministic.
- Missing evidence fails closed.
- Nonqualifying source evidence fails closed.
- Owner scope cannot expand.
- Limit cannot expand.
- Stale evidence fails closed.
- Role overlap fails closed.
- Eligible output permits only future-authorization preparation.
- Future authorization remains separate and new.
- Source authorization cannot be reused.
- No production delivery occurs.
- No authorization is consumed.
- No retry occurs.
- No scheduler is enabled.
- No automatic rollout promotion occurs.
- Unknown evidence fields are discarded.
- Sensitive evidence is excluded.
- Runtime, scheduler, schema and UI remain unchanged.
- Historical safety tests pass.
- Full regression passes.

## Next checkpoint

v266: saved-search notification production delivery pilot supervised execution manual rollout consideration implementation
