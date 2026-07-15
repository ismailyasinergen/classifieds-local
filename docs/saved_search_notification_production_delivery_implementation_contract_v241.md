# v241 — Saved-Search Notification Production Delivery Implementation Contract

## Checkpoint identity

- Base:
  `project-checkpoint-v240-saved-search-notification-persistent-audit-operator-shared-shell-integration-closeout-audit`
- Target:
  `project-checkpoint-v241-saved-search-notification-production-delivery-implementation-contract`
- Marker:
  `V241_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_IMPLEMENTATION_CONTRACT`

## Purpose

v241 defines the fail-closed contract for the first production-capable
saved-search notification delivery implementation.

This checkpoint does not enable production delivery. It adds only a focused
contract test and this root document.

The implementation remains deferred to v242.

## Current safety baseline

The current package continues to preserve:

- v222 explicit-send behavior restricted to the safe test backend.
- v224 rollback and audit hardening.
- v225 production-delivery design safeguards.
- v233 persistent audit storage and runtime behavior.
- v234–v240 staff operator, navigation and shared-shell safeguards.
- No production delivery bypass.
- No automatic scheduling.
- No production credentials in the repository.
- No migration after `0016`.

## v242 implementation scope

v242 may modify exactly:

1. `backend/config/settings.py`
2. `backend/listings/saved_search_notification_email_sender.py`
3. `backend/listings/management/commands/process_saved_search_notifications.py`
4. `backend/listings/test_saved_search_notification_production_delivery_implementation_v242.py`
5. `docs/saved_search_notification_production_delivery_implementation_v242.md`

No other implementation file belongs to the v242 scope.

## Default-off feature gate

`backend/config/settings.py` may introduce one non-secret boolean gate:

`SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED`

Requirements:

- Default value is `False`.
- The value is environment controlled.
- No SMTP password, API key, provider token or recipient address is committed.
- A disabled gate refuses production delivery before email backend access.
- Existing development and test behavior remains unchanged.

## Explicit command confirmation

Production delivery requires both:

- `--execute-production-send`
- `--confirm-production-delivery`

The command remains dry-run by default.

Supplying only one production flag must fail closed.

The existing test-backend execution path must remain separate and must not
become a production bypass.

## Mandatory owner scope

The first production implementation is deliberately owner-scoped.

Requirements:

- `--owner-id` is mandatory.
- Global all-owner production execution is forbidden in v242.
- An unknown owner fails closed.
- Only saved searches owned by the requested owner are considered.
- Only enabled and notification-opted-in saved searches are eligible.
- Existing due and cooldown rules remain authoritative.

## Bounded batch

Production execution requires an explicit `--limit`.

Requirements:

- Maximum accepted production limit is 25.
- Zero, negative, malformed or excessive values fail closed.
- Selection order is deterministic.
- The selected batch never exceeds 25.
- Zero eligible rows performs no delivery and returns a safe summary.

## Production backend policy

Before recipient processing, v242 must reject known non-production backends:

- Locmem.
- Dummy.
- Console.
- File-based backend.

SMTP and explicitly configured custom production backends may be accepted.

Backend validation must occur before:

- Querying recipient addresses for delivery.
- Rendering email content for delivery.
- Updating timestamps.
- Attempting provider communication.

## Idempotency and timestamp rules

`last_notification_sent_at` may change only after successful delivery.

It must not change for:

- Configuration refusal.
- Backend refusal.
- Rendering failure.
- Provider failure.
- Unexpected exception.

The same due saved search must not be delivered twice during one invocation.

Existing `last_notification_checked_at`, due-window and cooldown semantics
remain authoritative and must not be weakened.

## Persistent audit outcomes

v242 reuses the existing `SavedSearchNotificationAuditEvent` model and current
persistent audit writer.

The implementation must persist bounded, sanitized outcomes for:

- Configuration refusal.
- Delivery attempt.
- Delivery success.
- Delivery failure.

Requirements:

- No new audit model.
- No new migration.
- No editable Django admin registration.
- Stable delivery fingerprints.
- Sanitized and bounded metadata.
- No email body, recipient address, credential or raw provider response in
  metadata.

## Failure isolation

A failure for one saved search must not abort later eligible items.

The final command summary includes bounded counts for:

- Attempted.
- Succeeded.
- Failed.
- Refused.

Unexpected exceptions must be converted into sanitized operator-facing
messages and persistent failure audit records.

Provider response bodies and authentication details must never be printed.

## Privacy and secret handling

The implementation must not print or persist:

- Recipient email addresses.
- Owner email addresses.
- Saved-search query contents.
- Rendered email bodies.
- SMTP usernames or passwords.
- Provider API keys or tokens.
- Raw provider response bodies.

Credentials remain deployment-supplied environment values.

Documentation may use placeholder variable names but no real-looking
credential values.

## Scheduler boundary

v242 remains operator-invoked.

It must not add:

- A background worker.
- Celery.
- Cron configuration.
- Automatic scheduler delivery.
- Startup-time delivery.
- Request-time delivery.

`backend/listings/saved_search_notification_scheduler.py` remains unchanged.

## Rollback compatibility

Production delivery must preserve:

- Existing read-only rollback reporting.
- Existing explicit rollback behavior.
- Existing rollback authorization boundaries.
- Stable delivery fingerprints.
- Operator visibility into partial batch failures.

Production execution must not silently roll back successful deliveries when a
later item fails.

## Protected surfaces

v242 does not modify:

- `backend/listings/models.py`
- `backend/listings/admin.py`
- `backend/listings/urls.py`
- Migration `0016`
- Any new migration
- Scheduler
- Audit model
- Persistent audit writer
- Runtime adapter
- Email renderer
- Operator query service
- Operator view
- Operator template
- `backend/templates/base.html`
- Historical v222–v241 tests or documents

## Required v242 tests

The implementation test must cover at minimum:

- Feature gate defaults off.
- Disabled setting refuses before backend access.
- Both production confirmation flags are required.
- Owner ID is mandatory.
- Limit is mandatory and bounded to 25.
- Unknown owner fails closed.
- Locmem, dummy, console and file backends are rejected.
- A configured production backend can deliver.
- Only enabled, opted-in, due saved searches are selected.
- Owner isolation.
- Deterministic batch order.
- Successful delivery advances `last_notification_sent_at` once.
- Failed delivery preserves `last_notification_sent_at`.
- Refused delivery preserves `last_notification_sent_at`.
- No duplicate delivery in one invocation.
- Persistent refused, attempted, succeeded and failed audit outcomes.
- Sanitized audit metadata.
- Per-item failure isolation.
- Sanitized command summary.
- No recipient or credential leakage.
- Existing v222 test-backend path remains green.
- Existing v224 rollback path remains green.
- Existing v225 production design audit remains green.
- Existing v240 operator closeout remains green.
- No migration `0017`.
- Full regression passes.

## v241 scope

The v241 commit contains exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_implementation_contract_v241.py`
2. `docs/saved_search_notification_production_delivery_implementation_contract_v241.md`

## Next checkpoint

v242: saved-search notification production delivery implementation
