# v250 — Saved-Search Notification Production Delivery Controlled Rollout Contract

## Checkpoint identity

- Base:
  `project-checkpoint-v249-saved-search-notification-production-delivery-operator-runbook-closeout-audit`
- Target:
  `project-checkpoint-v250-saved-search-notification-production-delivery-controlled-rollout-contract`
- Marker:
  `V250_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_CONTROLLED_ROLLOUT_CONTRACT`

## Purpose

v250 defines the contract for a controlled production rollout of saved-search
notification delivery.

The contract governs staged, explicitly approved and evidence-backed production
runs. It does not itself send email or change production behavior.

Every production invocation remains:

- Manually initiated
- Single-owner scoped
- Explicitly bounded
- Protected by two production confirmation flags
- Preceded by strict readiness and preview
- Followed by persistent audit verification
- Blocked by explicit stop conditions

## Exact v250 scope

v250 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_controlled_rollout_contract_v250.py`
2. `docs/saved_search_notification_production_delivery_controlled_rollout_contract_v250.md`

## Proposed v251 implementation scope

v251 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_controlled_rollout_v251.py`
2. `docs/saved_search_notification_production_delivery_controlled_rollout_v251.md`

The v251 implementation is documentation and test only.

It must not modify:

- Settings
- Production sender
- Production delivery command
- Readiness service
- Readiness command
- Scheduler
- Models
- Admin
- URLs
- Templates
- Migrations

The v250 contract is forward-compatible and does not require future v251 files
to remain absent.

## Rollout principles

The controlled rollout must follow these principles:

- No automatic phase progression.
- No global all-owner production execution.
- No multi-owner command execution.
- One approved owner per production invocation.
- One approved phase limit per invocation.
- The preview owner and production owner must match.
- The preview limit and production limit must match.
- Every phase requires a new go or stop decision.
- Every progression decision requires reviewer approval.
- An open incident blocks progression.
- A stopped phase must not resume without fresh authorization.

## Phase 0 - Preflight and authorization

Phase 0 performs no production delivery.

Required evidence:

- Change-record identifier
- Operator identity
- Reviewer identity
- Approved target owner
- Approved phase
- Approved limit
- Approved execution window
- Rollback owner
- Confirmation that no concurrent run targets the same owner

Run strict readiness:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

Capture sanitized readiness evidence:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

A result other than `ready` is a mandatory stop condition.

The readiness result must remain valid immediately before preview and
production execution.

## Phase 1 - Single-owner pilot

Phase 1 uses:

- Exactly one approved owner
- An explicit limit from 1 through 3
- One preview
- At most one production invocation before review

Preview pattern:

    docker compose exec -T web python manage.py process_saved_search_notifications --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

Production pattern:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

Progression requires all go gates to pass.

A single delivery failure, configuration refusal, audit gap, timestamp
inconsistency or unresolved incident stops the rollout.

## Phase 2 - Limited owner-scoped expansion

Phase 2 uses:

- One approved owner per invocation
- An explicit limit from 4 through 10
- Fresh strict readiness before each invocation
- A matching owner-scoped preview
- Manual reviewer approval after every invocation

Preview pattern:

    docker compose exec -T web python manage.py process_saved_search_notifications --owner-id <POSITIVE_OWNER_ID> --limit <4-10>

Production pattern:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <4-10>

A rollout cohort may contain more than one approved owner, but each owner must
be processed through a separate command invocation, separate preview, separate
evidence package and separate go or stop decision.

## Phase 3 - Expanded owner-scoped validation

Phase 3 uses:

- One approved owner per invocation
- An explicit limit from 11 through 25
- No command limit above 25
- Fresh readiness and preview for every invocation
- Full audit and timestamp verification before another invocation

Preview pattern:

    docker compose exec -T web python manage.py process_saved_search_notifications --owner-id <POSITIVE_OWNER_ID> --limit <11-25>

Production pattern:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <11-25>

Phase 3 does not authorize automatic scheduling or global execution.

## Phase 4 - Stabilization and closeout review

Phase 4 performs no automatic expansion.

The reviewer must reconcile all approved phase evidence:

- Readiness results
- Preview summaries
- Delivery summaries
- Persistent audit sequences
- Sent-timestamp evidence
- Duplicate-attempt checks
- Refusal classifications
- Failure classifications
- Rollback decisions
- Incident references
- Owner and limit approvals

The rollout is not complete while any delivery, audit, timestamp, privacy or
provider incident remains unresolved.

## Required go gates

Every go decision requires:

- Strict readiness passes.
- Sanitized readiness JSON is retained.
- Authorized owner scope is documented.
- The bounded preview matches the approved owner and limit.
- Production uses both explicit confirmation flags.
- Failed count is zero.
- Unexpected refusal count is zero.
- Delivery counts reconcile.
- Persistent audit sequence is complete.
- Sent-timestamp evidence is consistent.
- Duplicate-attempt review is clean.
- No provider anomaly is present.
- No privacy or secret incident is open.
- Previous phase evidence is approved.

Skipped items may exist only when their sanitized classification is understood
and documented.

No phase progresses automatically.

## Mandatory stop conditions

Stop immediately when:

- Readiness status is not `ready`.
- The feature gate is disabled.
- The email backend is rejected.
- The default sender is missing.
- Owner identity is uncertain.
- Owner authorization is missing.
- Another operator may be running the same owner scope.
- Preview differs from the approved scope.
- The requested limit is outside the approved phase band.
- A configuration refusal is reported.
- A delivery failure is reported.
- Persistent audit evidence is incomplete.
- Sent-timestamp evidence is inconsistent.
- Duplicate-attempt protection activates unexpectedly.
- Provider behavior is unexpected.
- Sanitized counts cannot be reconciled.
- An unknown reason code appears.
- Private data or a secret may have appeared.
- An incident remains open.

A stopped rollout requires fresh investigation and authorization before any
additional production invocation.

## Persistent audit gate

The read-only audit interface remains:

    /staff/saved-search-notification-audit/

The expected successful sequence remains:

1. `delivery_attempted`
2. `delivery_succeeded`
3. `sent_timestamp_recorded`

The expected failed sequence includes:

1. `delivery_attempted`
2. `delivery_failed`

For every applicable attempt verify:

- Correct owner scope
- Expected attempt identity
- Sanitized reason code
- Expected event ordering
- Terminal event presence
- Sent-timestamp evidence after success
- No sent timestamp after failure
- No unexpected duplicate attempt
- No unexplained audit gap

Audit rows must not be edited or deleted.

## Rollback and recovery gate

Inspect deployed controls before rollback:

    docker compose exec -T web python manage.py process_saved_search_notifications --help

Use only source-verified rollback controls already covered by the audited
rollback workflow.

Before rollback apply:

- Review the original delivery attempt.
- Review persistent audit evidence.
- Verify the affected owner and saved-search attempt.
- Run the existing rollback preview.
- Obtain explicit approval.
- Preserve the original attempt identity.

After rollback:

- Verify rollback audit evidence.
- Verify restored timestamp state.
- Verify unrelated timestamps remain unchanged.
- Record the sanitized rollback result.
- Reassess whether the rollout remains stopped.

Never use:

- Direct SQL repair
- Django shell timestamp repair
- Manual timestamp edits
- Manual audit-event deletion
- Unsupported rollback options
- Attempt UUID rewriting
- Fingerprint rewriting
- Blind retry
- Evidence concealment

## Evidence package

Each phase evidence package must contain:

- Change-record identifier
- Rollout phase
- Operator identity
- Reviewer identity
- UTC start timestamp
- UTC finish timestamp
- Target owner identifier
- Approved phase limit
- Sanitized readiness result
- Sanitized preview summary
- Sanitized delivery summary
- Persistent audit verification result
- Sent-timestamp verification result
- Duplicate-attempt verification result
- Go or stop decision
- Rollback decision
- Incident reference when applicable

Evidence must not contain private notification payloads or secrets.

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

Permitted retained evidence is limited to sanitized statuses, stable reason
codes, aggregate counts, approved identifiers, limits, timestamps and
change-record references.

## Prohibited actions

The controlled rollout must explicitly prohibit:

- Automatic phase promotion
- Global all-owner execution
- Multi-owner command execution
- Limit above 25
- Limit outside the approved phase band
- Owner change without new approval
- Limit increase without new approval
- Readiness bypass
- Preview bypass
- Production-confirmation bypass
- Manual sent-timestamp edit
- Manual audit-event deletion
- Direct SQL repair
- Django shell timestamp repair
- Credential logging
- Recipient payload logging
- Saved-search payload logging
- Automatic scheduler enablement
- Celery enablement
- Cron enablement
- Startup-time delivery
- Request-time delivery
- Blind retry
- Silent partial-failure handling

## Runtime and schema boundary

v250 and the proposed v251 implementation introduce no change to:

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

v251 is accepted only when:

- Its scope is exactly the two contracted files.
- All five rollout phases are documented.
- Phase limits are exactly 1-3, 4-10 and 11-25.
- Phase progression is manual.
- Every invocation remains single-owner scoped.
- Strict readiness is required before every phase.
- Preview owner and limit match production owner and limit.
- Both production confirmation flags remain mandatory.
- Go and stop gates are explicit.
- Persistent audit and timestamp verification are explicit.
- Duplicate-attempt review is explicit.
- Open incidents block progression.
- Rollback uses only existing audited controls.
- Privacy and secret exclusions are explicit.
- No runtime, scheduler, schema or UI changes occur.
- Focused v250-v251 tests pass.
- Historical production-delivery safety tests pass.
- The complete regression suite remains green.

## Next checkpoint

v251: saved-search notification production delivery controlled rollout implementation
