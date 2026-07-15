# v247 — Saved-Search Notification Production Delivery Operator Runbook Contract

## Checkpoint identity

- Base:
  `project-checkpoint-v246-saved-search-notification-production-delivery-operational-readiness-closeout-audit`
- Target:
  `project-checkpoint-v247-saved-search-notification-production-delivery-operator-runbook-contract`
- Marker:
  `V247_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATOR_RUNBOOK_CONTRACT`

## Purpose

v247 defines the contract for the saved-search notification production-delivery
operator runbook.

The future runbook will guide an authorized operator through readiness
verification, one owner-scoped and bounded production run, persistent audit
verification, safe stop conditions, rollback decision-making and incident
escalation.

v247 is contract-only. It does not change delivery behavior or add automation.

## Exact v247 scope

v247 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_operator_runbook_contract_v247.py`
2. `docs/saved_search_notification_production_delivery_operator_runbook_contract_v247.md`

## Proposed v248 implementation scope

v248 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_operator_runbook_v248.py`
2. `docs/saved_search_notification_production_delivery_operator_runbook_v248.md`

The v248 implementation is documentation and test only.

It excludes settings, production runtime, readiness runtime, scheduler, models,
admin, URLs, templates and migrations.

The v247 contract test is forward-compatible and does not require the future
v248 files to remain absent.

## Required runbook sections

The implementation must contain:

1. Purpose and audience
2. Authority and change record
3. Preflight readiness
4. Environment and backend verification
5. Owner selection
6. Bounded preview
7. Production execution
8. Stop conditions
9. Result verification
10. Persistent audit verification
11. Failure isolation
12. Rollback and recovery
13. Incident escalation
14. Privacy and secret handling
15. Post-run evidence
16. Prohibited actions

## Operator authority

The runbook must require:

- An authorized operator
- A named reviewer or approver when organizational policy requires one
- A change-ticket or incident identifier
- A clearly identified target owner
- A documented execution window
- A documented rollback owner
- Confirmation that no concurrent operator is running the same owner scope

The runbook must not encourage anonymous or unrecorded production execution.

## Preflight readiness

The first executable step is the read-only readiness command:

    python manage.py check_saved_search_notification_production_readiness

The runbook must also document strict mode:

    python manage.py check_saved_search_notification_production_readiness --strict

Strict mode is the required pre-production gate.

The runbook may document sanitized JSON evidence:

    python manage.py check_saved_search_notification_production_readiness --json

A readiness status other than `ready` is a mandatory stop condition.

The operator must not bypass a failed readiness result.

## Environment and backend verification

The runbook must explain that readiness verifies:

- The production-delivery feature gate is declared and enabled.
- An email backend is configured.
- The backend is not locmem, dummy, console or file-based.
- A default sender is configured.
- Both production confirmation controls remain packaged.
- Positive owner scoping remains packaged.
- Explicit bounded limits remain packaged.
- The maximum production batch remains 25.

The output reports classifications and status only. It must not reveal raw
backend paths, sender values or credentials.

## Owner selection

The runbook must require one known, positive owner identifier.

The operator must verify the owner against the approved change record before
execution.

The runbook must prohibit:

- Missing owner scope
- Zero or negative owner IDs
- Guessed owner IDs
- Global all-owner production execution
- Expanding scope during an active run without a new approval

## Bounded preview

Before production execution, the operator must use the existing non-delivery
preview behavior of:

    python manage.py process_saved_search_notifications

The final runbook must document the source-verified owner and limit options
needed for the intended preview.

Preview output must remain sanitized.

Preview is not permission to send. Production execution still requires the
separate explicit production flags.

## Production execution

The runbook must document the existing guarded pattern:

    python manage.py process_saved_search_notifications \
      --execute-production-send \
      --confirm-production-delivery \
      --owner-id <POSITIVE_OWNER_ID> \
      --limit <1-25>

The runbook must state that:

- Both production confirmation flags are mandatory.
- A positive owner ID is mandatory.
- An explicit limit is mandatory.
- The limit must be between 1 and 25.
- The feature gate must already be enabled.
- The configured backend must pass readiness checks.
- The command remains per-item failure isolated.
- Refusal or failure counts must be reviewed before any subsequent run.

The runbook must not offer a bypass form of the command.

## Mandatory stop conditions

The operator must stop when:

- Readiness status is not `ready`.
- The feature gate is disabled.
- The email backend is rejected.
- The default sender is missing.
- Owner identity or authorization is uncertain.
- The requested limit is outside 1 through 25.
- An unexpected configuration refusal is reported.
- An unexpected delivery failure is reported.
- Persistent audit evidence is incomplete.
- Sent-timestamp evidence is inconsistent.
- Provider behavior differs from the approved expectation.
- Another operator may be running the same scope.
- The sanitized output cannot be reconciled with the approved change record.

Stopping means no additional production invocation until the issue is reviewed.

## Result verification

After execution, the operator must record the sanitized summary and reconcile:

- Requested limit
- Candidate count
- Delivered count
- Skipped count
- Refused count
- Failed count

The runbook must not direct the operator to copy recipient addresses, saved
search names, querystrings, email subjects or email bodies into the change
record.

## Persistent audit verification

The operator must verify the existing read-only audit interface:

    /staff/saved-search-notification-audit/

The operator must confirm the expected persistent sequence where applicable:

- `delivery_attempted`
- `delivery_succeeded` or `delivery_failed`
- `sent_timestamp_recorded`

The runbook must require verification of:

- Owner scope
- Delivery-attempt identity
- Sanitized reason codes
- Expected event ordering
- Sent-timestamp evidence
- Absence of unexpected duplicate attempts

The runbook must not instruct an operator to edit audit rows.

## Failure isolation

The runbook must explain that one failed saved search does not authorize:

- Re-running the whole owner scope blindly
- Increasing the limit
- Disabling safeguards
- Deleting audit evidence
- Manually advancing notification timestamps

The operator must classify the failure, preserve evidence and decide whether a
smaller approved retry or escalation is appropriate.

## Rollback and recovery

Rollback must use the existing audited rollback workflow established by the
project.

The runbook must require a preview before any explicit rollback operation.

The final implementation must reference only source-verified rollback controls.
It must not invent unsupported command options.

The operator must stop and escalate rather than guess rollback syntax.

The runbook must prohibit:

- Direct SQL timestamp edits
- Django shell timestamp edits
- Audit-event deletion
- Rewriting attempt UUIDs
- Rewriting fingerprints
- Concealing a partial failure
- Retrying without reviewing the original audit evidence

## Incident escalation

Escalation is required when:

- Provider behavior is unexpected.
- Audit writes fail.
- Timestamp recording fails.
- Duplicate-attempt protection activates unexpectedly.
- Delivery counts cannot be reconciled.
- Sanitized output indicates an unknown reason code.
- A credential may have appeared in output.
- Unauthorized execution is suspected.
- Manual database changes are discovered.
- The operator cannot prove the final state.

The runbook must direct the operator to preserve logs, stop additional delivery
and attach the incident reference to the change record.

## Privacy and secret handling

The runbook and retained evidence must never include:

- SMTP passwords
- SMTP usernames when treated as credentials
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

Only sanitized statuses, stable check IDs, stable reason codes and aggregate
counts may be retained.

## Post-run evidence

The runbook must require:

- Change-record identifier
- Operator identity
- UTC start timestamp
- UTC finish timestamp
- Target owner identifier
- Requested limit
- Sanitized readiness result
- Sanitized delivery summary
- Persistent audit verification result
- Sent-timestamp verification result
- Rollback decision
- Reviewer identity when required
- Incident reference when applicable

The evidence must be sufficient to reconstruct what the operator intended and
what the system reported without exposing private notification data.

## Prohibited actions

The runbook must explicitly prohibit:

- Global all-owner production execution
- A limit above 25
- Readiness-check bypass
- Production-confirmation bypass
- Owner-scope bypass
- Manual notification timestamp edits
- Manual audit-event deletion
- Credential logging
- Recipient or query payload logging
- Automatic scheduler enablement
- Celery or cron enablement
- Startup-time delivery
- Request-time delivery
- Unreviewed repeated execution
- Silent handling of partial failure

## Existing safety boundary

v248 must not modify or weaken:

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
- Sanitized production command output
- Read-only readiness checks
- The separate locmem-only test-send path
- The nonautomatic scheduler boundary

## Schema and UI boundary

v247 and the proposed v248 implementation introduce no:

- Model change
- Migration
- Admin mutation feature
- URL
- Template
- Browser execution control
- Background worker
- Celery integration
- Cron configuration
- Startup execution
- Request-time delivery
- Automatic production delivery

The latest listings migration remains:

`0016_savedsearchnotificationauditevent`

Migration `0017` remains absent.

## Acceptance gate

v248 is accepted only when:

- Its scope is exactly the two contracted files.
- Every required section is present.
- Every command reference matches currently packaged controls.
- The readiness step precedes production execution.
- Owner scope and limit boundaries are explicit.
- Mandatory stop conditions are explicit.
- Audit and timestamp verification are explicit.
- Rollback guidance uses only existing audited controls.
- Privacy and secret prohibitions are explicit.
- No protected runtime, schema or UI file changes.
- Focused v247–v248 tests pass.
- Historical delivery, readiness and audit tests pass.
- The complete regression suite remains green.

## Next checkpoint

v248: saved-search notification production delivery operator runbook implementation
