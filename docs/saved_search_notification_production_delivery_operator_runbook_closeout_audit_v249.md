# v249 — Saved-Search Notification Production Delivery Operator Runbook Closeout Audit

## Checkpoint identity

- Base:
  `project-checkpoint-v248-saved-search-notification-production-delivery-operator-runbook`
- Target:
  `project-checkpoint-v249-saved-search-notification-production-delivery-operator-runbook-closeout-audit`
- Marker:
  `V249_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATOR_RUNBOOK_CLOSEOUT_AUDIT`

## Purpose

v249 closes the saved-search notification production-delivery operator-runbook
lane.

This checkpoint is audit-only. It adds one focused closeout test module and
this root document.

It does not change the runbook, production-delivery runtime, readiness runtime,
scheduler, schema, admin, URLs, templates or browser UI.

## Exact v249 scope

v249 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_operator_runbook_closeout_audit_v249.py`
2. `docs/saved_search_notification_production_delivery_operator_runbook_closeout_audit_v249.md`

## Closed runbook gates

The closeout audit verifies that:

- The v247 runbook contract remains packaged.
- The v248 runbook implementation remains packaged.
- v247 retains its exact two-file contract scope.
- v248 retains its exact two-file implementation scope.
- v249 retains its exact two-file audit scope.
- All sixteen required runbook sections remain present.
- The sections remain in their contracted order.
- Authority and change-record checks precede execution.
- Strict readiness precedes preview.
- Preview precedes production execution.
- Stop conditions precede rollback or repeated execution.
- Post-run evidence and prohibited actions remain explicit.

## Readiness gate

The required strict readiness command remains:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

The sanitized JSON evidence command remains:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

The closeout audit confirms:

- Local development settings safely report `not_ready`.
- Valid production-like settings report `ready`.
- The readiness command remains read-only.
- The readiness command exposes only `--strict` and `--json`.
- Readiness execution opens no email-provider connection.
- Readiness execution performs no production delivery.
- A readiness result other than `ready` remains a mandatory stop condition.

## Owner-scoped bounded preview

The documented preview remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --owner-id <POSITIVE_OWNER_ID> --limit <1-25>

The preview remains:

- Owner-scoped
- Explicitly bounded
- Non-production
- Separate from production confirmation
- Sanitized
- Mandatory before production execution

The preview command contains neither production confirmation flag.

## Production execution boundary

The guarded production command remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-25>

The closeout audit confirms:

- Both production confirmation flags remain mandatory.
- A positive owner identifier remains mandatory.
- An explicit limit remains mandatory.
- The limit remains between 1 and 25.
- The maximum production batch remains 25.
- Global all-owner execution remains prohibited.
- One failure remains isolated from later items.
- A failed item does not authorize blind full-scope retry.
- A second production run requires review of the first result.

## Mandatory stop conditions

The operator must continue to stop when:

- Readiness status is not `ready`.
- The feature gate is disabled.
- The email backend is rejected.
- The default sender is missing.
- Owner identity or authorization is uncertain.
- The requested limit is outside 1 through 25.
- Another operator may be running the same owner scope.
- An unexpected configuration refusal occurs.
- An unexpected delivery failure occurs.
- Persistent audit evidence is incomplete.
- Sent-timestamp evidence is inconsistent.
- Provider behavior is unexpected.
- Sanitized output cannot be reconciled.
- An unknown reason code appears.
- Private data or a secret may have appeared in output.
- Duplicate-attempt protection activates unexpectedly.

Stopping means no additional production invocation until review is complete.

## Result and persistent audit verification

The runbook continues to require reconciliation of:

- Requested limit
- Candidate count
- Delivered count
- Skipped count
- Refused count
- Failed count

The read-only audit interface remains:

    /staff/saved-search-notification-audit/

The expected persistent sequence remains:

1. `delivery_attempted`
2. `delivery_succeeded` or `delivery_failed`
3. `sent_timestamp_recorded` after successful delivery

The operator must continue to verify:

- Correct owner scope
- Expected attempt identity
- Stable sanitized reason codes
- Expected event ordering
- Sent-timestamp evidence
- Missing terminal events
- Unexpected duplicate attempts
- Unexplained audit gaps

Audit rows remain append-only and must not be edited or deleted.

## Rollback and recovery boundary

The canonical deployed-help command remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --help

The runbook continues to require:

- Inspection of deployed command help before rollback.
- Use of only source-verified rollback controls.
- A rollback preview before apply.
- Review of the original delivery attempt.
- Review of persistent audit evidence.
- Explicit approval before rollback apply.
- Verification of rollback audit evidence afterward.
- Verification that unrelated timestamps were not changed.

The runbook continues to prohibit:

- Guessing rollback option names
- Unsupported rollback flags
- Direct SQL repair
- Django shell timestamp repair
- Manual sent-timestamp edits
- Manual audit-event deletion
- Attempt UUID rewriting
- Fingerprint rewriting
- Evidence concealment
- Unreviewed repeated rollback

When deployed help differs from the reviewed runbook, the operator must stop
and escalate.

## Incident escalation

Escalation remains mandatory when:

- Provider behavior is unexpected.
- Audit writes fail.
- Timestamp recording fails.
- Duplicate-attempt protection activates unexpectedly.
- Counts cannot be reconciled.
- An unknown reason code appears.
- A credential or private payload may have appeared.
- Unauthorized execution is suspected.
- Manual database changes are discovered.
- Rollback behavior differs from the reviewed version.
- The final state cannot be proven.

Additional production delivery must stop while an incident remains unresolved.

## Privacy and secret boundary

Runbook evidence must never contain:

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

Permitted retained evidence remains limited to:

- Stable statuses
- Stable check identifiers
- Stable reason codes
- Boolean pass states
- Aggregate counts
- Approved owner identifier
- Approved bounded limit
- UTC timestamps
- Change-record identifier
- Incident identifier

## Runtime and schema boundary

v249 introduces no changes to:

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
- Celery
- Cron
- Startup execution
- Request-time delivery
- Database migrations

The latest listings migration remains:

`0016_savedsearchnotificationauditevent`

Migration `0017` remains absent.

## Validation matrix

The checkpoint must pass:

- Host-side v248 package verification
- Django system checks
- Migration dry-run checks
- Applied migration verification
- Category-seed verification
- Docker Compose configuration validation
- Readiness command smoke checks
- Production command-help smoke checks
- Focused v249 closeout tests
- v247–v249 transition tests
- Readiness and runbook guard tests
- Historical delivery, rollback and audit safety tests
- Complete Django regression

The final commit must contain exactly the two v249 audit files.

## Closeout result

The operator-runbook lane is closed when all validations pass and:

- The working tree is clean.
- The v249 tag resolves to final HEAD.
- The parent remains the tagged v248 checkpoint.
- The commit scope is exactly two files.
- No migration 0017 exists.
- No protected runtime checksum changes.
- No remote push has occurred.

## Next checkpoint

v250: saved-search notification production delivery controlled rollout contract
