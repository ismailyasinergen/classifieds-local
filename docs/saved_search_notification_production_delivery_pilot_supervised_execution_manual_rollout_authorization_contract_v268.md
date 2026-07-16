# v268 — Saved-Search Notification Production Delivery Pilot Supervised Execution Manual Rollout Authorization Contract

## Checkpoint identity

- Base:
  `project-checkpoint-v267-saved-search-notification-production-delivery-pilot-supervised-execution-manual-rollout-consideration-closeout-audit`
- Target:
  `project-checkpoint-v268-saved-search-notification-production-delivery-pilot-supervised-execution-manual-rollout-authorization-contract`
- Marker:
  `V268_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_AUTHORIZATION_CONTRACT`

## Purpose

v268 defines the contract for preparing a new, bounded and one-shot
manual-rollout authorization after the v265–v267 consideration lane has
closed successfully.

The contract is documentation and test only.

It performs no production delivery.

## Exact v268 scope

v268 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_authorization_contract_v268.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_authorization_contract_v268.md`

## Proposed v269 implementation scope

v269 may modify exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_authorization_v269.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_authorization_v269.md`

v269 remains documentation and test only.

## Contract boundary

v268 defines authorization evidence and validation boundaries only.

It does not:

- Generate an executable production command
- Execute production delivery
- Consume authorization
- Reuse historical authorization
- Retry delivery
- Enable a scheduler
- Enable automatic retry
- Promote rollout automatically
- Change the production feature gate
- Mutate database state

## Closed consideration source

The source consideration must remain:

- Decision `eligible_to_prepare_future_authorization`
- Eligibility flag true
- Empty reason-code collection
- Sanitized
- Bound to a complete immutable snapshot
- Bound to all 47 v267 authorization preconditions
- Owner-scoped
- Limit-bounded
- Free of production action during consideration

Any source mismatch fails closed.

## Required authorization fields

The contract defines exactly 46 unique fields covering:

- New authorization identity
- Historical source bindings
- Source consideration eligibility
- Source owner and limit
- Authorization owner and limit
- Seven human-control roles
- Readiness and preview evidence
- Provider, sender and backend evidence
- Command and freeze fingerprints
- Authorization creation and expiration
- Both production confirmations
- Explicit feature-gate expectation
- Consumption and invocation counters
- Explicit no-action flags
- Authorization state
- Reason-code collection

## Decisions

The only authorization decisions are:

- `not_authorized`
- `authorized_to_prepare_single_manual_execution`

`not_authorized` retains fail-closed precedence.

The positive decision permits preparation of one bounded manual execution only.

It does not execute that operation.

## Reason-code package

The contract defines 41 unique and ordered reason codes:

- 14 completeness reasons
- 10 source-consideration reasons
- 12 owner, limit, role, freshness and fingerprint reasons
- 5 prohibited-action reasons

The four families are disjoint.

## New authorization identity

The authorization identifier must be new.

It cannot equal the historical source authorization identifier.

The historical authorization remains evidence only and cannot be:

- Reopened
- Renewed
- Reused
- Reconsumed
- Converted into a new authorization
- Treated as an executable command

A reuse attempt fails closed.

## Owner boundary

The authorization owner must:

- Be a positive integer
- Match the source owner
- Be the only owner in scope

The maximum owner count is:

`1`

Global all-owner and multi-owner execution remain prohibited.

## Limit boundary

The source approved limit, source considered limit and authorization limit must
each be integers from one through three.

The authorization limit cannot exceed the source considered limit.

The source considered limit cannot exceed the source approved limit.

The maximum authorization limit is:

`3`

Limit expansion fails closed.

## Required roles

The seven required roles are:

1. Decision owner
2. Authorizing operator
3. Evidence reviewer
4. Privacy reviewer
5. Incident reviewer
6. Rollback reviewer
7. Incident commander

## Role separation

The contract requires:

- Authorizing operator differs from decision owner
- Authorizing operator differs from every reviewer
- Decision owner differs from every reviewer
- Evidence, privacy, incident and rollback reviewers are pairwise distinct
- Incident commander differs from authorizing operator
- Incident commander differs from decision owner
- Incident commander differs from rollback reviewer

Role overlap fails closed.

## Readiness freshness

Readiness evidence remains current only when:

    0 <= current_timestamp - readiness_generated_at <= 300

The exact 300-second boundary is valid.

Stale, future-dated or changed readiness evidence fails closed.

## Preview freshness

Preview evidence remains current only when:

    0 <= current_timestamp - preview_generated_at <= 300

The exact 300-second boundary is valid.

Stale, future-dated or changed preview evidence fails closed.

## Provider-state freshness

Provider, sender and email-backend state remains current only when:

    0 <= current_timestamp - provider_state_generated_at <= 300

The exact 300-second boundary is valid.

A stale or changed provider-state package fails closed.

## Authorization lifetime

Authorization remains valid only when:

    0 <= current_timestamp - authorization_created_at <= 600

and:

    current_timestamp <= authorization_expires_at

The exact 600-second lifetime boundary is valid.

Future-dated, missing or expired authorization fails closed.

## Fingerprint boundary

The authorization binds:

- Readiness evidence fingerprint
- Preview evidence fingerprint
- Provider-state fingerprint
- Sender-state fingerprint
- Email-backend-state fingerprint
- Authorization command fingerprint
- Pre-send freeze fingerprint

Any change requires a new authorization package.

Silent fingerprint mismatch acceptance is prohibited.

## Immutable bindings

The immutable authorization snapshot contains exactly:

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

These 14 bindings cannot be rewritten after authorization preparation.

## Production confirmations

Both confirmations remain mandatory:

- `--execute-production-send`
- `--confirm-production-delivery`

The authorization evidence records their explicit approval.

v268 does not execute either confirmation.

## Initial authorization state

A prepared authorization must begin with:

- State `prepared`
- Consumption count `0`
- Production invocation count `0`
- Production delivery performed `false`
- Retry performed `false`
- Scheduler enabled `false`
- Automatic promotion performed `false`
- Empty reason-code collection

Any preconsumed or preexecuted state fails closed.

## Single-execution preparation boundary

A positive authorization decision permits preparation only when:

- Decision is `authorized_to_prepare_single_manual_execution`
- Reason-code collection is empty
- Authorization identifier is new
- Historical authorization remains nonreusable
- Owner is positive and singular
- Limit is between one and three
- Execution limit cannot exceed authorization limit
- Readiness evidence is current
- Preview evidence is current
- Provider, sender and backend state is current
- Command and freeze fingerprints are current
- Both production confirmations are present
- Authorization is unconsumed and unexpired
- One-shot consumption occurs only at execution
- Retry and automatic promotion remain disabled
- Scheduler remains disabled

## Positive result boundary

The positive contract summary may return:

- Authorization decision
- Authorized boolean
- Owner identifier
- Approved limit
- Single-execution requirements

It must return:

- No production command
- No provider payload
- No recipient payload
- No credential
- No executed delivery
- No consumed authorization

## Strict evidence allowlist

The authorization evidence allowlist exactly matches the 46 required fields.

Unknown fields are excluded.

Sensitive fields are excluded.

Input decision and reason-code values cannot override computed outcomes in the
future implementation.

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

## Prohibited actions

v268 prohibits:

- Production delivery during authorization preparation
- Authorization consumption during authorization preparation
- Delivery retry during authorization preparation
- Scheduler enablement
- Automatic rollout promotion
- Production feature-gate mutation
- Owner-scope expansion
- Limit expansion
- Historical authorization reuse
- Consideration result used as executable command
- Global all-owner execution
- Multi-owner execution
- Blind retry
- Direct SQL repair
- Django shell timestamp repair
- Privacy sanitizer bypass
- Authorization-decision spoofing
- Reason-code spoofing
- Silent fingerprint mismatch acceptance
- Automatic authorization renewal

## Pure contract helper

The reference contract helper is:

- Pure
- Deterministic
- In-memory
- Nonexecuting

Tests verify that it does not call:

- `subprocess.run`
- Django management commands
- Django email connection creation

## Production-command boundary

The guarded production-command shape remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

v268 neither constructs nor executes this command.

## Readiness boundary

The report-only readiness commands remain:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

and:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

Authorization preparation must use regenerated current evidence.

## No-production-action boundary

v268 performs no:

- Production delivery
- Email rendering
- Email connection
- Provider call
- Management command invocation
- Subprocess invocation
- Database mutation

## No-authorization-consumption boundary

v268 does not:

- Consume authorization
- Reopen authorization
- Renew authorization
- Revoke authorization
- Modify authorization state
- Reuse historical authorization

## No-retry boundary

v268 performs no:

- Blind retry
- Manual retry
- Automatic retry
- Scheduler retry
- Multi-owner retry
- Global all-owner retry

## No-scheduler boundary

v268 cannot:

- Enable a scheduler
- Add a periodic task
- Add cron execution
- Add startup execution
- Add a background worker
- Enable automatic delivery

## No-automatic-promotion boundary

v268 cannot:

- Promote rollout automatically
- Increase owner scope
- Increase authorization limit
- Enable the production feature gate
- Execute a production command
- Renew authorization automatically

## Runtime and schema boundary

v268 introduces no changes to:

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

## v269 implementation boundary

v269 may implement only a pure, deterministic reference evaluator for this
contract.

It must remain documentation and test only.

It must:

- Validate all 46 required fields
- Emit only the 41 ordered reason codes
- Enforce one-owner scope
- Enforce limit one through three
- Enforce role separation
- Enforce freshness and expiration
- Enforce fingerprint immutability
- Require both production confirmations
- Start unconsumed and nonexecuted
- Return no production command
- Perform no production delivery
- Consume no authorization
- Perform no retry
- Enable no scheduler
- Perform no automatic promotion

## Next checkpoint

v269: saved-search notification production delivery pilot supervised execution manual rollout authorization implementation
