# v252 — Saved-Search Notification Production Delivery Controlled Rollout Closeout Audit

## Checkpoint identity

- Base:
  `project-checkpoint-v251-saved-search-notification-production-delivery-controlled-rollout`
- Target:
  `project-checkpoint-v252-saved-search-notification-production-delivery-controlled-rollout-closeout-audit`
- Marker:
  `V252_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_CONTROLLED_ROLLOUT_CLOSEOUT_AUDIT`

## Purpose

v252 closes the controlled production-rollout documentation and test lane.

This checkpoint is audit-only. It adds one closeout test module and one root
documentation file.

It does not execute production delivery and does not alter production runtime.

## Exact v252 scope

v252 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_controlled_rollout_closeout_audit_v252.py`
2. `docs/saved_search_notification_production_delivery_controlled_rollout_closeout_audit_v252.md`

## Closed package boundary

The closeout verifies that:

- The v250 controlled-rollout contract remains packaged.
- The v251 controlled-rollout implementation remains packaged.
- v250 retains its exact two-file contract scope.
- v251 retains its exact two-file implementation scope.
- v252 retains its exact two-file audit scope.
- Runtime, scheduler, schema and UI surfaces remain unchanged.
- Migration 0016 remains the latest listings migration.
- Migration 0017 remains absent.

## Phase model closeout

The five-phase rollout remains:

1. Phase 0 — preflight and authorization
2. Phase 1 — single-owner pilot
3. Phase 2 — limited owner-scoped expansion
4. Phase 3 — expanded owner-scoped validation
5. Phase 4 — stabilization and closeout review

Phase 0 and Phase 4 remain nonproduction phases.

Phase progression remains manual and requires reviewer approval.

## Production limit bands

The closed limit bands remain:

- Phase 1: 1 through 3
- Phase 2: 4 through 10
- Phase 3: 11 through 25

The production batch maximum remains 25.

A limit outside the approved phase band remains a mandatory stop condition.

## Readiness boundary

Every production phase continues to require strict readiness:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

Sanitized readiness evidence continues to use:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

The readiness command remains:

- Read-only
- Non-delivering
- Limited to `--strict` and `--json`
- Free of email-provider connection attempts
- Sanitized
- Fail-closed in strict mode

Default local development configuration continues to report `not_ready`.

Valid production-like configuration continues to report `ready`.

## Phase 1 command boundary

Phase 1 preview remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

Phase 1 production remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

## Phase 2 command boundary

Phase 2 preview remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --owner-id <POSITIVE_OWNER_ID> --limit <4-10>

Phase 2 production remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <4-10>

## Phase 3 command boundary

Phase 3 preview remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --owner-id <POSITIVE_OWNER_ID> --limit <11-25>

Phase 3 production remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <11-25>

## Owner and preview invariants

Every production invocation remains:

- Single-owner scoped
- Positive-owner scoped
- Explicitly limited
- Preceded by a matching preview
- Protected by both production confirmation flags

The preview owner must match the production owner.

The preview limit must match the production limit.

Multi-owner command execution remains prohibited.

Global all-owner execution remains prohibited.

## Go-decision closeout

Progression continues to require all of the following:

- Strict readiness passed.
- Sanitized readiness JSON was retained.
- Preview owner matched production owner.
- Preview limit matched production limit.
- Both production confirmation flags were used.
- Failed count equals zero.
- Unexpected refusal count equals zero.
- Delivery counts reconcile.
- Persistent audit sequence is complete.
- Sent-timestamp evidence is consistent.
- Duplicate-attempt review is clean.
- No provider anomaly exists.
- No privacy or secret incident is open.
- Reviewer approved progression.

No phase progresses automatically.

## Stop-decision closeout

The rollout continues to stop when:

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

A stop decision prohibits further production invocation until fresh review and
authorization.

## Persistent audit boundary

The read-only audit interface remains:

    /staff/saved-search-notification-audit/

The successful sequence remains:

1. `delivery_attempted`
2. `delivery_succeeded`
3. `sent_timestamp_recorded`

The failed sequence remains:

1. `delivery_attempted`
2. `delivery_failed`

The operator continues to verify:

- Correct owner scope
- Correct attempt identity
- Stable sanitized reason code
- Correct event order
- Terminal event presence
- No unexpected duplicate attempt
- No unexplained audit gap
- No sent timestamp after failure

Audit rows must not be edited or deleted.

## Rollback boundary

The deployed command surface must be inspected before rollback:

    docker compose exec -T web python manage.py process_saved_search_notifications --help

Rollback continues to require:

- Source-verified deployed controls
- Original attempt review
- Persistent audit review
- Existing rollback preview
- Explicit reviewer approval
- Post-rollback audit verification
- Restored timestamp verification
- Verification that unrelated timestamps remain unchanged

The rollout continues to prohibit:

- Unsupported rollback options
- Blind retry
- Direct SQL repair
- Django shell timestamp repair
- Manual timestamp edits
- Manual audit-event deletion
- Attempt UUID rewriting
- Fingerprint rewriting
- Evidence concealment

## Evidence-record closeout

The required evidence fields remain:

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

## Privacy and secret boundary

The evidence package must not retain:

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

Suspected exposure remains a mandatory stop and escalation condition.

## Prohibited actions

The closed rollout lane continues to prohibit:

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

v252 introduces no changes to:

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

## Validation matrix

The checkpoint must pass:

- Exact clean v251 base verification
- v251 package and scope verification
- Host-side v252 AST validation
- Django system checks
- Migration dry-run checks
- Applied migration verification
- Category-seed verification
- Docker Compose validation
- Readiness command smoke tests
- Production command-help smoke test
- Focused v252 closeout tests
- v250-v252 controlled-rollout transition tests
- v247-v252 runbook and rollout guard tests
- Historical production-delivery safety tests
- Complete Django regression
- Protected-file checksum verification
- Exact two-file commit-scope verification

## Closeout result

The controlled-rollout lane is closed only when:

- All focused tests pass.
- Historical safety tests pass.
- Full regression passes.
- The commit contains exactly two v252 files.
- The v252 tag resolves to final HEAD.
- The parent remains the tagged v251 checkpoint.
- The working tree is clean.
- Runtime, scheduler, schema and UI remain unchanged.
- Migration 0017 remains absent.
- No remote push occurs.

## Next checkpoint

v253: saved-search notification production delivery pilot readiness contract
