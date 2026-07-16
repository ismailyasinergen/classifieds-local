# v269 — Saved-Search Notification Production Delivery Pilot Supervised Execution Manual Rollout Authorization Implementation

## Checkpoint identity

- Base:
  `project-checkpoint-v268-saved-search-notification-production-delivery-pilot-supervised-execution-manual-rollout-authorization-contract`
- Target:
  `project-checkpoint-v269-saved-search-notification-production-delivery-pilot-supervised-execution-manual-rollout-authorization`
- Marker:
  `V269_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_AUTHORIZATION`

## Purpose

v269 implements the pure reference evaluator defined by the v268
manual-rollout authorization contract.

The implementation remains documentation and test only.

It performs no production delivery.

## Exact v269 scope

v269 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_authorization_v269.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_authorization_v269.md`

## Proposed v270 closeout scope

v270 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_authorization_closeout_audit_v270.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_authorization_closeout_audit_v270.md`

v270 remains documentation and test only.

## Implementation boundary

The v269 evaluator is:

- Pure
- Deterministic
- In-memory
- Fail-closed
- Strictly allowlisted
- Nonexecuting

It validates authorization evidence only.

## Contract continuity

v269 preserves:

- 46 required authorization fields
- 14 immutable bindings
- 7 required roles
- 7 role-separation rules
- 2 authorization decisions
- 41 ordered reason codes
- 18 single-execution requirements
- 1-owner maximum
- Limit maximum 3
- Readiness freshness 300 seconds
- Preview freshness 300 seconds
- Provider-state freshness 300 seconds
- Authorization lifetime 600 seconds

## Evaluation context

The evaluator context binds:

- Current timestamp
- Expected readiness fingerprint
- Expected preview fingerprint
- Expected provider-state fingerprint
- Expected sender-state fingerprint
- Expected email-backend-state fingerprint
- Expected authorization-command fingerprint
- Expected pre-send-freeze fingerprint

Any mismatch fails closed.

## Final result

The evaluator returns exactly:

- Decision
- Authorized boolean
- Ordered reason codes
- Sanitized evidence
- Immutable snapshot
- Single-execution requirements
- Owner identifier
- Approved limit
- Production command placeholder
- Production-delivery flag
- Authorization-consumption flag

The production command is always `None`.

Production delivery is always `false`.

Authorization consumption is always `false`.

## Decisions

The only decisions remain:

- `not_authorized`
- `authorized_to_prepare_single_manual_execution`

`not_authorized` has fail-closed precedence.

## Positive decision boundary

`authorized_to_prepare_single_manual_execution` means only that a later,
separately supervised execution package may be prepared.

It does not execute delivery.

It does not consume authorization.

## Ordered reason package

The evaluator emits only the 41 v268 reason codes:

- 14 completeness reasons
- 10 source-consideration reasons
- 12 owner, limit, role, freshness and fingerprint reasons
- 5 prohibited-action reasons

All 41 reason codes are independently reachable.

Returned ordering is deterministic.

## Completeness evaluation

The evaluator rejects missing:

- Authorization identifier
- Source consideration identifier
- Source change-record identifier
- Historical source authorization identifier
- Owner identifier
- Approved limit
- Authorizing operator
- Required reviewer identity
- Readiness evidence
- Preview evidence
- Provider-state evidence
- Command fingerprint
- Freeze fingerprint
- Authorization time window

## Source consideration evaluation

The source must remain:

- Decision `eligible_to_prepare_future_authorization`
- Eligibility true
- Empty source reason-code collection
- Sanitized
- Immutable-snapshot-complete
- Authorization-preconditions-complete

Any mismatch fails closed.

## Historical authorization boundary

The new authorization identifier cannot equal the historical authorization
identifier.

Historical authorization reuse produces:

`historical_authorization_reuse_attempted`

## Owner boundary

The source owner and authorization owner must be positive integers.

The authorization owner must match the source owner.

The considered source owner scope must contain exactly that one owner.

Expansion produces:

`owner_scope_expanded`

The maximum owner count remains:

`1`

## Limit boundary

The source approved limit, source considered limit and authorization limit must
be integers from one through three.

The source considered limit cannot exceed the source approved limit.

The authorization limit cannot exceed the source considered limit.

Expansion produces:

`limit_expanded`

The maximum authorization limit remains:

`3`

## Role-separation boundary

The required roles remain:

1. Decision owner
2. Authorizing operator
3. Evidence reviewer
4. Privacy reviewer
5. Incident reviewer
6. Rollback reviewer
7. Incident commander

The evaluator rejects:

- Authorizing-operator overlap
- Decision-owner overlap
- Duplicate reviewer identities
- Incident-commander and rollback-reviewer overlap

## Readiness freshness

Readiness evidence is accepted only when:

    0 <= current_timestamp - readiness_generated_at <= 300

The exact 300-second boundary is valid.

Changed, stale or future-dated evidence produces:

`readiness_evidence_stale_or_changed`

## Preview freshness

Preview evidence is accepted only when:

    0 <= current_timestamp - preview_generated_at <= 300

The exact 300-second boundary is valid.

Changed, stale or future-dated evidence produces:

`preview_evidence_stale_or_changed`

## Provider-state freshness

Provider-state evidence is accepted only when:

    0 <= current_timestamp - provider_state_generated_at <= 300

The provider, sender and email-backend fingerprints must all match.

Changed, stale or future-dated state produces:

`provider_state_stale_or_changed`

## Command and freeze boundary

The authorization command fingerprint and pre-send freeze fingerprint must
match the evaluation context.

A mismatch produces:

`command_or_freeze_fingerprint_changed`

## Authorization lifetime

Authorization is accepted only when:

    0 <= current_timestamp - authorization_created_at <= 600

and:

    authorization_created_at < authorization_expires_at

and:

    authorization_expires_at - authorization_created_at <= 600

and:

    current_timestamp <= authorization_expires_at

The exact 600-second boundary is valid.

Invalid, future-dated or expired authorization produces:

`authorization_expired_or_future_dated`

## Production confirmations

Both confirmations remain mandatory:

- `--execute-production-send`
- `--confirm-production-delivery`

Missing confirmation fails closed through the source-precondition boundary.

v269 does not execute either confirmation.

## Initial state boundary

The authorization must begin:

- State `prepared`
- Consumption count `0`
- Production invocation count `0`
- Production delivery performed `false`
- Retry performed `false`
- Scheduler enabled `false`
- Automatic promotion performed `false`

Any violation fails closed.

## Prohibited-action evaluation

The evaluator emits explicit reasons when:

- Production delivery was performed
- Authorization was consumed
- A production invocation already occurred
- Retry was performed
- Scheduler was enabled
- Automatic promotion was performed

## Decision-spoofing protection

Input `reason_codes` cannot control the computed result.

Input authorization state cannot force a positive result.

The evaluator overwrites:

- Sanitized `reason_codes`
- Sanitized `authorization_state`

with computed values.

## Strict sanitizer

The sanitizer retains only the exact 46-field contract allowlist.

Unknown fields are discarded.

Sensitive fields are discarded.

Sensitive values do not appear in output.

## Privacy exclusions

The implementation excludes:

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

The evaluator returns the exact 14 immutable bindings:

- Authorization identifier
- Source consideration identifier
- Source change-record identifier
- Historical source authorization identifier
- Owner identifier
- Approved limit
- Readiness fingerprint
- Preview fingerprint
- Provider-state fingerprint
- Sender-state fingerprint
- Email-backend-state fingerprint
- Command fingerprint
- Freeze fingerprint
- Authorization expiration

Snapshot generation is deterministic.

## Single-execution requirements

A positive result returns the exact 18 v268 single-execution requirements.

A negative result returns none.

## No-external-action proof

Tests verify that evaluation does not call:

- `subprocess.run`
- Django management commands
- Django email connection creation

The evaluator performs no database mutation.

## Production-command boundary

The guarded production-command shape remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

v269 neither constructs nor executes this command.

## Readiness boundary

The report-only readiness commands remain:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

and:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

Readiness evaluation opens no email connection.

## No-production-action boundary

v269 performs no:

- Production delivery
- Email rendering
- Email connection
- Provider call
- Management command invocation
- Subprocess invocation
- Database mutation

## No-authorization-consumption boundary

v269 does not:

- Consume authorization
- Reopen authorization
- Renew authorization
- Revoke authorization
- Modify authorization state
- Reuse historical authorization

## No-retry boundary

v269 performs no:

- Blind retry
- Manual retry
- Automatic retry
- Scheduler retry
- Multi-owner retry
- Global all-owner retry

## No-scheduler boundary

v269 cannot:

- Enable a scheduler
- Add a periodic task
- Add cron execution
- Add startup execution
- Add a background worker
- Enable automatic delivery

## No-automatic-promotion boundary

v269 cannot:

- Promote rollout automatically
- Expand owner scope
- Expand authorization limit
- Enable the production feature gate
- Execute a production command
- Renew authorization automatically

## No-repair boundary

v269 does not:

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

v269 introduces no changes to:

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

## v270 closeout boundary

v270 may audit only the v268–v269 authorization lane.

It must verify:

- All 41 reasons remain reachable
- Reason ordering remains deterministic
- Owner scope remains one
- Limit remains one through three
- Role separation remains fail-closed
- Freshness and lifetime boundaries remain inclusive
- Fingerprint changes remain rejected
- Sanitizer and immutable snapshot remain exact
- Positive result remains preparation only
- Production delivery remains absent
- Authorization consumption remains absent
- Retry remains absent
- Scheduler remains disabled
- Automatic promotion remains disabled
- Runtime and schema remain unchanged

## Next checkpoint

v270: saved-search notification production delivery pilot supervised execution manual rollout authorization closeout audit
