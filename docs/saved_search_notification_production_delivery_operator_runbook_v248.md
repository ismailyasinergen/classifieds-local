# v248 — Saved-Search Notification Production Delivery Operator Runbook

## Checkpoint identity

- Base:
  `project-checkpoint-v247-saved-search-notification-production-delivery-operator-runbook-contract`
- Target:
  `project-checkpoint-v248-saved-search-notification-production-delivery-operator-runbook`
- Marker:
  `V248_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATOR_RUNBOOK`

## Purpose and audience

This runbook is for an authorized production operator responsible for a
controlled saved-search notification delivery run.

It covers one approved owner scope and one explicitly bounded execution.

It does not authorize:

- Global delivery across all owners
- Automatic scheduling
- Background-worker activation
- Request-time delivery
- Safeguard bypass
- Manual database repair

Every production run must be tied to an approved change record or incident
record.

## Authority and change record

Before running any command, record:

- Change-record identifier
- Operator identity
- Reviewer or approver identity when required
- Target owner identifier
- Requested limit
- Approved execution window
- Rollback owner
- Incident reference when applicable

Confirm that:

- The operator is authorized.
- The owner identifier is known and positive.
- The requested limit is between 1 and 25.
- No other operator is running the same owner scope.
- The approved record matches the intended environment.
- The rollback owner is available during the execution window.

Stop when any authority or scope detail is missing or uncertain.

## Preflight readiness

Run the strict, read-only readiness gate first:

    docker compose exec -T web \
      python manage.py \
      check_saved_search_notification_production_readiness \
      --strict

The strict command must finish successfully.

A readiness result other than `ready` is a mandatory stop condition.

Do not bypass a failed readiness result.

Capture sanitized JSON evidence separately:

    docker compose exec -T web \
      python manage.py \
      check_saved_search_notification_production_readiness \
      --json

Retain only the sanitized readiness result:

- Overall status
- Stable check identifiers
- Stable reason codes
- Aggregate counts

Do not retain raw configuration values.

## Environment and backend verification

The readiness result must confirm that:

- The production-delivery feature gate is declared.
- The feature gate is enabled.
- An email backend is configured.
- The backend is not locmem.
- The backend is not dummy.
- The backend is not console.
- The backend is not file-based.
- A default sender is configured.
- Both production confirmation controls remain packaged.
- Positive owner scoping remains packaged.
- Explicit bounded limits remain packaged.
- The production batch maximum remains 25.

The operator must not print, copy or retain:

- The raw backend path
- The default sender value
- SMTP usernames or passwords
- API keys
- Access tokens

Stop when provider behavior or environment identity differs from the approved
change record.

## Owner selection

Use exactly one approved positive owner identifier.

Before preview:

- Compare the owner ID with the approved change record.
- Confirm that the owner ID is greater than zero.
- Confirm that the owner scope has not changed.
- Confirm that no concurrent run targets the same owner.
- Confirm that the requested limit is still approved.

Never:

- Guess an owner ID.
- Use zero or a negative owner ID.
- Omit owner scope.
- Expand the run to all owners.
- Change the owner during an active execution.
- Reuse approval from a different owner.

## Bounded preview

Run the existing non-production preview with the same owner and limit intended
for production:

    docker compose exec -T web \
      python manage.py \
      process_saved_search_notifications \
      --owner-id <POSITIVE_OWNER_ID> \
      --limit <1-25>

The preview command must not contain:

- `--execute-production-send`
- `--confirm-production-delivery`

Review the sanitized preview summary.

Verify:

- The owner scope matches the approved record.
- The requested limit matches the approved record.
- Candidate counts are plausible.
- Skipped or refused classifications are understood.
- No unexpected failure is reported.
- No private saved-search payload appears in output.

Preview does not authorize delivery.

Stop when the preview cannot be reconciled with the approved scope.

## Production execution

Only after successful readiness and preview, run:

    docker compose exec -T web \
      python manage.py \
      process_saved_search_notifications \
      --execute-production-send \
      --confirm-production-delivery \
      --owner-id <POSITIVE_OWNER_ID> \
      --limit <1-25>

Required controls:

- `--execute-production-send`
- `--confirm-production-delivery`
- A positive `--owner-id`
- An explicit `--limit`
- A limit between 1 and 25

Both production confirmation flags are mandatory.

The owner and limit must be identical to the approved preview unless a new
approval is recorded.

Do not:

- Increase the limit after preview.
- Change the owner after preview.
- omit either confirmation flag.
- Retry the entire owner scope automatically.
- Run a second production command before verifying the first result.

The production sender remains per-item failure isolated. One failed item does
not authorize expansion or blind repetition.

## Stop conditions

Stop immediately when:

- Readiness status is not `ready`.
- The feature gate is disabled.
- The email backend is rejected.
- The default sender is missing.
- Owner identity or authorization is uncertain.
- The requested limit is outside 1 through 25.
- Another operator may be running the same owner scope.
- An unexpected configuration refusal is reported.
- An unexpected delivery failure is reported.
- Persistent audit evidence is incomplete.
- Sent-timestamp evidence is inconsistent.
- Provider behavior is unexpected.
- Sanitized output cannot be reconciled with the change record.
- An unknown reason code appears.
- A secret or private payload may have appeared in output.
- Duplicate-attempt protection activates unexpectedly.

Stopping means:

- Do not invoke production delivery again.
- Preserve sanitized logs.
- Preserve the change-record reference.
- Begin incident review when required.
- Do not alter database state manually.

## Result verification

Record the sanitized command summary.

Reconcile:

- Requested limit
- Candidate count
- Delivered count
- Skipped count
- Refused count
- Failed count

Confirm that:

- Counts are internally consistent.
- The owner scope is unchanged.
- The result matches the approved execution.
- Any refusal has a known sanitized reason code.
- Any failure is treated as an isolated item.
- No second production run has started.

Do not copy:

- Recipient addresses
- Saved-search names
- Saved-search querystrings
- Email subjects
- Email bodies
- Provider response bodies
- Raw tracebacks

## Persistent audit verification

Open the existing read-only staff audit interface:

    /staff/saved-search-notification-audit/

Verify the expected persistent sequence for each applicable attempt:

1. `delivery_attempted`
2. `delivery_succeeded` or `delivery_failed`
3. `sent_timestamp_recorded` when delivery succeeds

Verify:

- Correct owner scope
- Expected delivery-attempt identity
- Sanitized reason codes
- Expected event ordering
- Sent-timestamp evidence after successful delivery
- No unexpected duplicate attempt
- No missing terminal event
- No unexplained audit gap

The audit interface is read-only.

Never edit or delete audit rows.

Stop and escalate when audit evidence is incomplete or inconsistent.

## Failure isolation

A failed saved search remains isolated.

One failure does not authorize:

- Re-running every candidate
- Increasing the limit
- Changing the owner
- Disabling safeguards
- Deleting audit evidence
- Manually advancing a sent timestamp
- Concealing a partial failure

For each failure:

- Preserve sanitized evidence.
- Record the stable reason code.
- Verify whether a persistent failure audit exists.
- Verify that no successful sent timestamp was incorrectly recorded.
- Decide whether a smaller separately approved retry is appropriate.
- Escalate when the final state cannot be proven.

Do not retry until the original attempt and audit sequence have been reviewed.

## Rollback and recovery

Before using rollback controls, inspect the deployed command help:

Canonical deployed-help command:

    docker compose exec -T web python manage.py process_saved_search_notifications --help

    docker compose exec -T web \
      python manage.py \
      process_saved_search_notifications \
      --help

Use only rollback controls that are present in the deployed command help and
already covered by the project’s audited rollback workflow.

Do not guess rollback option names.

Before any rollback apply operation:

- Verify the original owner scope.
- Verify the original audit evidence.
- Identify the exact saved-search attempt.
- Run the existing rollback preview.
- Review the preview with the rollback owner.
- Record explicit approval for apply.
- Preserve the original attempt identity and evidence.

After rollback:

- Verify the rollback audit event.
- Verify the restored timestamp state.
- Verify that unrelated timestamps were not changed.
- Record the sanitized rollback result.
- Decide whether a new separately approved delivery is appropriate.

Never use:

- Direct SQL timestamp edits
- Django shell timestamp edits
- Manual audit-event deletion
- Attempt UUID rewriting
- Fingerprint rewriting
- Unsupported rollback flags
- Unreviewed repeated rollback
- Evidence concealment

When deployed help differs from the reviewed runbook, stop and escalate.

## Incident escalation

Escalate when:

- Provider behavior is unexpected.
- Audit writes fail.
- Timestamp recording fails.
- Duplicate-attempt protection activates unexpectedly.
- Counts cannot be reconciled.
- An unknown reason code appears.
- A credential may have appeared in output.
- Private notification data may have appeared in output.
- Unauthorized execution is suspected.
- Manual database changes are discovered.
- The final state cannot be proven.
- Rollback help or behavior differs from the reviewed version.

Incident response:

1. Stop additional delivery.
2. Preserve sanitized command output.
3. Preserve readiness and preview evidence.
4. Preserve persistent audit evidence.
5. Record UTC timestamps.
6. Attach the incident identifier to the change record.
7. Notify the rollback owner and reviewer.
8. Do not attempt speculative repair.

## Privacy and secret handling

Never place the following in logs, tickets, screenshots or retained evidence:

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

Retain only:

- Stable marker
- Stable status
- Stable check identifier
- Stable reason code
- Boolean pass state
- Aggregate count
- Owner identifier approved for the run
- Requested bounded limit
- UTC timestamps
- Change or incident references

Redact unexpected private content before attaching evidence.

Treat any suspected secret exposure as an incident.

## Post-run evidence

Complete the change record with:

- Change-record identifier
- Operator identity
- Reviewer identity when required
- UTC start timestamp
- UTC finish timestamp
- Target owner identifier
- Requested limit
- Sanitized readiness result
- Sanitized preview summary
- Sanitized delivery summary
- Persistent audit verification result
- Sent-timestamp verification result
- Duplicate-attempt verification result
- Rollback decision
- Rollback result when applicable
- Incident reference when applicable

The evidence must show:

- What was approved
- What was previewed
- What was executed
- What the system reported
- What audit evidence was verified
- Whether rollback or escalation was required

The evidence must not expose private notification content.

## Prohibited actions

The following actions are prohibited:

- Global all-owner production execution
- Limit above 25
- Readiness bypass
- Production-confirmation bypass
- Owner-scope bypass
- Owner change after preview without new approval
- Limit increase after preview without new approval
- Manual sent-timestamp edit
- Manual audit-event deletion
- Direct SQL repair
- Django shell timestamp repair
- Credential logging
- Recipient payload logging
- Saved-search payload logging
- Provider response logging
- Automatic scheduler enablement
- Celery enablement
- Cron enablement
- Startup-time delivery
- Request-time delivery
- Unreviewed repeated execution
- Blind full-scope retry
- Silent partial-failure handling
- Unsupported rollback syntax
- Evidence concealment

## Existing safety boundary

v248 does not modify or weaken:

- The default-off production feature gate
- Double explicit production confirmation
- Positive owner scoping
- Explicit bounded limits
- Maximum production batch size of 25
- Known nonproduction-backend rejection
- Persistent delivery audit behavior
- Sent-timestamp rollback protection
- Duplicate-attempt protection
- Per-item failure isolation
- Sanitized production-command output
- Read-only readiness checks
- The separate locmem-only test-send path
- The nonautomatic scheduler boundary

## Schema and UI boundary

v248 introduces no change to:

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
- Database migrations

The latest listings migration remains:

`0016_savedsearchnotificationauditevent`

Migration `0017` remains absent.

## Completion checklist

The operator may close the change record only after confirming:

- Strict readiness passed.
- Sanitized JSON readiness evidence was retained.
- Owner-scoped bounded preview was reviewed.
- Production used both confirmation flags.
- Owner and limit matched the approved preview.
- Sanitized counts were reconciled.
- Persistent audit events were verified.
- Sent-timestamp evidence was verified.
- Duplicate-attempt state was reviewed.
- Failure isolation was respected.
- Rollback decision was recorded.
- Incident reference was recorded when applicable.
- No private content or secret was retained.
- No manual database change was performed.
- No additional production run remains unreviewed.

## Next checkpoint

v249: saved-search notification production delivery operator runbook closeout audit
