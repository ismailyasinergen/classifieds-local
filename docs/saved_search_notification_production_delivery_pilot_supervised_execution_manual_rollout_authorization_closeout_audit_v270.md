# v270 — Saved-Search Notification Production Delivery Pilot Supervised Execution Manual Rollout Authorization Closeout Audit

## Checkpoint identity

- Base:
  `project-checkpoint-v269-saved-search-notification-production-delivery-pilot-supervised-execution-manual-rollout-authorization`
- Target:
  `project-checkpoint-v270-saved-search-notification-production-delivery-pilot-supervised-execution-manual-rollout-authorization-closeout-audit`
- Marker:
  `V270_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_AUTHORIZATION_CLOSEOUT_AUDIT`

## Purpose

v270 closes the manual-rollout authorization lane and terminates the extended
saved-search notification audit series.

No additional audit checkpoint is proposed.

After this checkpoint, project work returns to the product roadmap.

## Exact v270 scope

v270 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_authorization_closeout_audit_v270.py`
2. `docs/saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_authorization_closeout_audit_v270.md`

## Closed authorization lane

The following lane is closed:

1. v268 manual-rollout authorization contract
2. v269 manual-rollout authorization implementation
3. v270 manual-rollout authorization closeout audit

## Closed saved-search audit series

The wider saved-search notification audit sequence is now closed.

It is not extended to a v271 audit checkpoint.

Future work requires a concrete product, production-readiness or security need.

A new audit chain must not be created merely to continue checkpoint numbering.

## Final contract state

The closed authorization package retains:

- 46 required authorization fields
- 41 ordered reason codes
- 14 immutable bindings
- 7 required roles
- 7 role-separation rules
- 18 single-execution requirements
- 2 authorization decisions
- Maximum owner scope of 1
- Maximum authorization limit of 3
- Readiness freshness of 300 seconds
- Preview freshness of 300 seconds
- Provider-state freshness of 300 seconds
- Authorization lifetime of 600 seconds

## Final decisions

The only decisions remain:

- `not_authorized`
- `authorized_to_prepare_single_manual_execution`

`not_authorized` retains fail-closed precedence.

The positive result remains preparation-only.

## Final reason-code coverage

All 41 reason codes remain:

- Unique
- Deterministically ordered
- Independently reachable
- Divided into the four contracted families

No new reason code is introduced during closeout.

## Source-consideration boundary

Authorization still requires:

- Eligible source consideration
- Empty source reason-code collection
- Sanitized source evidence
- Complete immutable source snapshot
- Complete source authorization preconditions

Any mismatch remains fail-closed.

## Historical authorization boundary

The historical source authorization remains nonreusable.

A new authorization identifier must differ from the historical identifier.

Historical authorization cannot be:

- Reopened
- Renewed
- Reconsumed
- Converted into a new authorization
- Treated as an executable command

## Owner boundary

The owner must:

- Be a positive integer
- Match the source owner
- Be the only owner in scope

Maximum owner count remains:

`1`

Global all-owner and multi-owner execution remain prohibited.

## Limit boundary

The source approved limit, source considered limit and authorization limit
remain integers from one through three.

The source considered limit cannot exceed the source approved limit.

The authorization limit cannot exceed the source considered limit.

Maximum authorization limit remains:

`3`

## Role boundary

The required roles remain:

1. Decision owner
2. Authorizing operator
3. Evidence reviewer
4. Privacy reviewer
5. Incident reviewer
6. Rollback reviewer
7. Incident commander

Role overlap and reviewer duplication remain fail-closed.

## Freshness boundary

The inclusive freshness limits remain:

- Readiness evidence: 300 seconds
- Preview evidence: 300 seconds
- Provider, sender and backend state: 300 seconds
- Authorization lifetime: 600 seconds

Stale and future-dated evidence remains rejected.

## Fingerprint boundary

The evaluator remains bound to:

- Readiness fingerprint
- Preview fingerprint
- Provider-state fingerprint
- Sender-state fingerprint
- Email-backend-state fingerprint
- Authorization-command fingerprint
- Pre-send-freeze fingerprint

Any changed fingerprint remains rejected.

## Authorization-window boundary

Authorization remains valid only when:

    0 <= current_timestamp - authorization_created_at <= 600

and:

    authorization_created_at < authorization_expires_at

and:

    authorization_expires_at - authorization_created_at <= 600

and:

    current_timestamp <= authorization_expires_at

The exact 600-second boundary remains valid.

## Production-confirmation boundary

Both explicit controls remain mandatory:

- `--execute-production-send`
- `--confirm-production-delivery`

v270 does not execute either control.

## Initial-state boundary

Authorization must begin:

- State `prepared`
- Consumption count `0`
- Production invocation count `0`
- Production delivery performed `false`
- Retry performed `false`
- Scheduler enabled `false`
- Automatic promotion performed `false`

Preconsumed or preexecuted state remains rejected.

## Positive-result boundary

A positive result returns:

- Decision
- Authorized boolean
- Owner identifier
- Approved limit
- Single-execution requirements
- Sanitized evidence
- Immutable snapshot

It returns no production command.

It performs no production delivery.

It consumes no authorization.

## Strict sanitizer boundary

The sanitizer retains only the exact 46-field allowlist.

Unknown fields remain discarded.

Sensitive fields remain discarded.

Computed reason codes and authorization state remain unspoofable.

## Privacy boundary

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

The immutable snapshot remains exactly 14 fields and remains deterministic.

It contains authorization identity, source bindings, owner, limit, evidence
fingerprints, command and freeze fingerprints, and expiration.

## No-external-action proof

The closeout verifies that the evaluator does not call:

- `subprocess.run`
- Django management commands
- Django email connection creation

The evaluator performs no database mutation.

## Production-command boundary

The guarded command shape remains:

    docker compose exec -T web python manage.py process_saved_search_notifications --execute-production-send --confirm-production-delivery --owner-id <POSITIVE_OWNER_ID> --limit <1-3>

v270 neither constructs nor executes this command.

## Readiness boundary

The report-only readiness commands remain:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --strict

and:

    docker compose exec -T web python manage.py check_saved_search_notification_production_readiness --json

Readiness evaluation opens no email connection.

## No-production-action boundary

v270 performs no:

- Production delivery
- Email rendering
- Email connection
- Provider call
- Management command invocation
- Subprocess invocation
- Database mutation

## No-authorization-consumption boundary

v270 does not:

- Consume authorization
- Reopen authorization
- Renew authorization
- Revoke authorization
- Modify authorization state
- Reuse historical authorization

## No-retry boundary

v270 performs no:

- Blind retry
- Manual retry
- Automatic retry
- Scheduler retry
- Multi-owner retry
- Global all-owner retry

## No-scheduler boundary

v270 cannot:

- Enable a scheduler
- Add a periodic task
- Add cron execution
- Add startup execution
- Add a background worker
- Enable automatic delivery

## No-automatic-promotion boundary

v270 cannot:

- Promote rollout automatically
- Expand owner scope
- Expand authorization limit
- Enable the production feature gate
- Execute a production command
- Renew authorization automatically

## No-repair boundary

v270 does not:

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

v270 introduces no changes to:

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

## Release-readiness summary

The final audit package establishes:

- Consideration and authorization audit lanes are closed
- All 41 authorization reasons remain reachable
- Owner scope remains one
- Authorization limit remains three
- Freshness and lifetime boundaries remain enforced
- Historical authorization remains nonreusable
- Positive output remains preparation-only
- Production command remains absent
- Production delivery remains absent
- Authorization consumption remains absent
- Retry remains absent
- Scheduler remains disabled
- Automatic promotion remains disabled
- Sensitive evidence remains excluded
- Runtime, schema and UI remain unchanged
- Migration `0017` remains absent

## Audit-series closure

Saved-search notification audit status:

`closed`

Next audit checkpoint:

`none`

Next audit scope:

`none`

## Return to product roadmap

After successful completion of v270, the project returns to work that delivers
a concrete user, operational, deployment or security outcome.

New audit-only checkpoint chains should not be created without a specific,
documented need.

## Next project action

Return to the product roadmap.
