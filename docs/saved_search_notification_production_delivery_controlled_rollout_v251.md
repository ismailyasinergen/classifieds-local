# v251 — Saved-Search Notification Production Delivery Controlled Rollout

## Checkpoint identity

- Base:
  `project-checkpoint-v250-saved-search-notification-production-delivery-controlled-rollout-contract`
- Target:
  `project-checkpoint-v251-saved-search-notification-production-delivery-controlled-rollout`
- Marker:
  `V251_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_CONTROLLED_ROLLOUT`

## Purpose

This document implements the controlled-rollout operating model defined by
v250.

It provides executable phase checklists, go-or-stop decision rules, evidence
fields and explicit production boundaries.

It does not itself execute production delivery and does not modify production
runtime.

## Exact v251 scope

v251 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_controlled_rollout_v251.py`
2. `docs/saved_search_notification_production_delivery_controlled_rollout_v251.md`

## Proposed v252 closeout scope

v252 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_controlled_rollout_closeout_audit_v252.py`
2. `docs/saved_search_notification_production_delivery_controlled_rollout_closeout_audit_v252.md`

The v252 closeout remains documentation and test only.

## Global rollout rules

The following rules apply to every production phase:

- Phase progression is manual.
- Every progression requires reviewer approval.
- Every production command targets one approved owner.
- Every production command uses one explicit approved limit.
- Preview owner and production owner must match.
- Preview limit and production limit must match.
- Strict readiness must pass immediately before preview.
- Both production confirmation flags are mandatory.
- A failed item blocks phase progression.
- An unexpected refusal blocks phase progression.
- An open incident blocks phase progression.
- No phase may enable scheduling or background delivery.

## Phase 0 — Preflight and authorization

Production delivery is not allowed in Phase 0.

### Required authorization record

Record:

- Change-record identifier
- Operator identity
- Reviewer identity
- Approved owner identifier
- Approved rollout phase
- Approved phase limit
- Execution window
- Rollback owner
- Incident reference when applicable

Confirm:

- The owner identifier is positive.
- The phase limit is within the approved band.
- No concurrent run targets the same owner.
- The operator is authorized.
- The reviewer is available.
- No rollout-blocking incident remains open.

### Strict readiness

Run:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

The command must complete successfully.

A status other than `ready` means stop.

### Sanitized readiness evidence

Run:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

Retain only:

- Overall readiness status
- Stable check identifiers
- Stable reason codes
- Ready count
- Not-ready count
- Warning count

Do not retain raw settings, sender values or credentials.

## Phase 1 — Single-owner pilot

Phase 1 limit band is 1 through 3.

Only one approved owner may be processed in one invocation.

### Phase 1 preview

Run:

    docker compose exec -T web python manage.py process_saved_search_notifications --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

Verify:

- Owner matches the authorization record.
- Limit matches the authorization record.
- Candidate count is understood.
- Skipped classifications are understood.
- No unexpected refusal exists.
- No failure exists.
- Output is sanitized.

### Phase 1 production

Run:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

Do not run a second production command before completing audit verification and
a reviewer decision.

## Phase 2 — Limited owner-scoped expansion

Phase 2 limit band is 4 through 10.

Every owner requires:

- A separate authorization
- A separate strict readiness check
- A separate preview
- A separate production invocation
- A separate evidence record
- A separate go-or-stop decision

### Phase 2 preview

Run:

    docker compose exec -T web python manage.py process_saved_search_notifications --owner-id <POSITIVE_OWNER_ID> --limit <4-10>

### Phase 2 production

Run:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <4-10>

Processing multiple owners through one command invocation is prohibited.

## Phase 3 — Expanded owner-scoped validation

Phase 3 limit band is 11 through 25.

The maximum production limit remains 25.

### Phase 3 preview

Run:

    docker compose exec -T web python manage.py process_saved_search_notifications --owner-id <POSITIVE_OWNER_ID> --limit <11-25>

### Phase 3 production

Run:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <11-25>

A successful Phase 3 run does not authorize global or automatic execution.

## Phase 4 — Stabilization and closeout review

Production delivery is not allowed in Phase 4.

The reviewer must reconcile all phase evidence.

Confirm:

- Every owner had separate authorization.
- Every owner had separate readiness evidence.
- Every preview matched production owner and limit.
- Every production invocation used both confirmation flags.
- Failed count was zero for every progressed phase.
- Unexpected refusal count was zero.
- Delivery counts reconciled.
- Persistent audit sequences were complete.
- Sent-timestamp evidence was consistent.
- Duplicate-attempt reviews were clean.
- All rollback decisions were recorded.
- All incidents were resolved or explicitly transferred.

## Per-invocation execution checklist

Before production:

- Confirm approved change record.
- Confirm operator and reviewer identities.
- Confirm positive owner identifier.
- Confirm approved phase limit.
- Confirm no concurrent owner-scoped run.
- Run strict readiness.
- Retain sanitized readiness JSON.
- Run matching owner-scoped preview.
- Reconcile preview with approval.

During production:

- Use `--execute-production-send`.
- Use `--confirm-production-delivery`.
- Use the approved positive owner identifier.
- Use the approved phase limit.
- Do not alter owner or limit after preview.

After production:

- Reconcile sanitized delivery counts.
- Verify persistent audit sequence.
- Verify sent-timestamp evidence.
- Verify duplicate-attempt state.
- Record go or stop decision.
- Record rollback decision.
- Record incident reference when applicable.

## Go-decision requirements

A phase may progress only when all are true:

- Strict readiness passed.
- Sanitized readiness JSON was retained.
- Preview owner matched production owner.
- Preview limit matched production limit.
- Both production confirmations were used.
- Failed count equals zero.
- Unexpected refusal count equals zero.
- Delivery counts reconcile.
- Audit sequence is complete.
- Sent-timestamp evidence is consistent.
- Duplicate-attempt review is clean.
- No provider anomaly exists.
- No privacy or secret incident is open.
- Reviewer approved progression.

A go decision applies only to the documented phase and scope.

## Stop-decision reasons

Stop when any of the following occurs:

- Readiness is not ready.
- Owner authorization is missing.
- Owner scope mismatches.
- Phase limit mismatches.
- A concurrent owner-scoped run is suspected.
- Configuration refusal occurs.
- Delivery failure occurs.
- Audit sequence is incomplete.
- Sent timestamp is inconsistent.
- Duplicate-attempt anomaly occurs.
- Provider anomaly occurs.
- Counts cannot be reconciled.
- An unknown reason code appears.
- Private-data exposure is suspected.
- Secret exposure is suspected.
- An incident remains open.

After a stop decision:

- Do not run another production command.
- Preserve sanitized evidence.
- Record the incident or review reference.
- Review rollback requirements.
- Obtain fresh authorization before resuming.

## Persistent audit verification

Use the read-only audit interface:

    /staff/saved-search-notification-audit/

For successful delivery verify:

1. `delivery_attempted`
2. `delivery_succeeded`
3. `sent_timestamp_recorded`

For failed delivery verify:

1. `delivery_attempted`
2. `delivery_failed`

Also verify:

- Correct owner scope
- Correct attempt identity
- Stable sanitized reason code
- Correct event ordering
- Terminal event presence
- No unexpected duplicate attempt
- No unexplained audit gap
- No sent timestamp after failure

Audit rows must not be edited or deleted.

## Rollback decision

Inspect deployed controls first:

    docker compose exec -T web python manage.py process_saved_search_notifications --help

Use only source-verified rollback controls from the existing audited rollback
workflow.

Before rollback apply:

- Review original delivery evidence.
- Review persistent audit evidence.
- Confirm affected owner and attempt.
- Run the existing rollback preview.
- Obtain explicit reviewer approval.

After rollback:

- Verify rollback audit evidence.
- Verify restored timestamp state.
- Verify unrelated timestamps remain unchanged.
- Record the sanitized rollback result.
- Keep rollout status stopped until reauthorized.

Never guess rollback options.

## Evidence record

Record these fields:

- `change_record_id`
- `rollout_phase`
- `operator_identity`
- `reviewer_identity`
- `started_at_utc`
- `finished_at_utc`
- `owner_id`
- `approved_limit`
- `readiness_status`
- `readiness_ready_count`
- `readiness_not_ready_count`
- `preview_candidate_count`
- `preview_skipped_count`
- `delivery_delivered_count`
- `delivery_skipped_count`
- `delivery_refused_count`
- `delivery_failed_count`
- `audit_verified`
- `sent_timestamp_verified`
- `duplicate_attempt_verified`
- `decision`
- `rollback_decision`
- `incident_reference`

Do not include recipient addresses, saved-search payloads, rendered email
content or provider response bodies.

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

Suspected exposure requires a stop decision and incident escalation.

## Prohibited actions

The rollout prohibits:

- Automatic phase promotion
- Global all-owner production execution
- Multi-owner production invocation
- Phase limit above 25
- Phase limit outside the approved band
- Owner change without approval
- Limit change without approval
- Readiness bypass
- Preview bypass
- Production-confirmation bypass
- Blind retry
- Manual sent-timestamp edit
- Manual audit-event deletion
- Direct SQL repair
- Django shell timestamp repair
- Automatic scheduler enablement
- Celery enablement
- Cron enablement
- Startup-time delivery
- Request-time delivery
- Credential logging
- Recipient payload logging
- Saved-search payload logging
- Silent partial-failure handling

## Runtime and schema boundary

v251 introduces no changes to:

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

## Completion gate

v251 is complete only when:

- Its commit scope is exactly two files.
- All five phases remain documented.
- Production bands remain 1-3, 4-10 and 11-25.
- Phase progression remains manual.
- Every production invocation remains single-owner scoped.
- Strict readiness and preview precede production.
- Both production confirmation flags remain mandatory.
- Go and stop decisions are documented.
- Evidence fields are explicit.
- Runtime and schema remain unchanged.
- Focused and historical tests pass.
- Full regression passes.
- Working tree is clean.
- The v251 tag resolves to final HEAD.

## Next checkpoint

v252: saved-search notification production delivery controlled rollout closeout audit
