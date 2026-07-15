# v244 — Saved-Search Notification Production Delivery Operational Readiness Contract

## Checkpoint identity

- Base:
  `project-checkpoint-v243-saved-search-notification-production-delivery-closeout-audit`
- Target:
  `project-checkpoint-v244-saved-search-notification-production-delivery-operational-readiness-contract`
- Marker:
  `V244_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATIONAL_READINESS_CONTRACT`

## Purpose

v244 defines the contract for a read-only production-delivery operational
readiness preflight.

The future preflight will tell an operator whether the existing saved-search
production-delivery configuration is ready to use. It must not send email,
connect to an email provider, mutate saved searches, write audit events or
change notification timestamps.

v244 is contract-only. It does not implement the readiness service or command.

## Exact v244 scope

v244 modifies exactly:

1. `backend/listings/test_saved_search_notification_production_delivery_operational_readiness_contract_v244.py`
2. `docs/saved_search_notification_production_delivery_operational_readiness_contract_v244.md`

## Proposed v245 implementation scope

v245 may modify exactly:

1. `backend/listings/saved_search_notification_production_readiness.py`
2. `backend/listings/management/commands/check_saved_search_notification_production_readiness.py`
3. `backend/listings/test_saved_search_notification_production_delivery_operational_readiness_v245.py`
4. `docs/saved_search_notification_production_delivery_operational_readiness_v245.md`

The v245 scope excludes the existing production sender, production delivery
command, scheduler, settings, models, admin, URLs, templates and migrations.

## Read-only service contract

The future readiness service must:

- Be deterministic for the same settings and packaged source.
- Return structured data rather than print directly.
- Perform no email rendering.
- Perform no email delivery.
- Perform no SMTP or provider connection.
- Perform no database insert, update or delete.
- Create no `SavedSearchNotificationAuditEvent`.
- Mutate no saved-search notification timestamp.
- Read no provider credential value.
- Return only sanitized booleans, statuses, check IDs and reason codes.

## Required readiness checks

The service must expose these stable check IDs:

1. `feature_gate_declared`
2. `feature_gate_enabled`
3. `email_backend_configured`
4. `email_backend_allowed`
5. `default_sender_configured`
6. `double_confirmation_packaged`
7. `owner_scope_packaged`
8. `explicit_limit_packaged`
9. `batch_cap_packaged`

The checks verify that:

- `SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED` exists.
- The feature gate is currently enabled or disabled.
- `EMAIL_BACKEND` is configured.
- The backend is not locmem, dummy, console or file-based.
- `DEFAULT_FROM_EMAIL` is configured.
- Both explicit production confirmation flags remain packaged.
- A positive owner ID remains mandatory.
- An explicit limit remains mandatory.
- The production batch maximum remains 25.

## Status contract

Overall and individual check status values are limited to:

- `ready`
- `not_ready`
- `warning`

The structured result must contain:

- `marker`
- `status`
- `ready`
- `checks`
- `ready_count`
- `not_ready_count`
- `warning_count`

Each check result must contain:

- `check_id`
- `status`
- `passed`
- `reason_code`

## Stable reason codes

The contract reserves these sanitized reason codes:

- `ready`
- `feature_gate_missing`
- `feature_gate_disabled`
- `email_backend_missing`
- `email_backend_rejected`
- `default_sender_missing`
- `delivery_confirmation_missing`
- `owner_scope_missing`
- `explicit_limit_missing`
- `batch_cap_mismatch`

Reason codes must not contain configuration values, email addresses, saved
search data, provider responses or exception text.

## Management command contract

The future command is:

`check_saved_search_notification_production_readiness`

Supported options are:

- `--strict`
- `--json`

Default invocation:

- Produces a sanitized human-readable report.
- Returns normally even when the environment is not ready.
- Performs no delivery or mutation.

`--json`:

- Produces the same sanitized structured result as JSON.
- Does not include raw setting values or secrets.

`--strict`:

- Raises `CommandError` when the overall result is not ready.
- Still performs no delivery, provider connection or mutation.

The command must not accept delivery execution flags, owner IDs, recipient
addresses, provider credentials or saved-search query parameters.

## Privacy boundary

Human and JSON output must never include:

- Recipient addresses
- `DEFAULT_FROM_EMAIL` value
- Saved-search names
- Saved-search querystrings
- Rendered email subjects
- Rendered email bodies
- SMTP usernames or passwords
- API keys or tokens
- Provider response bodies
- Raw exception messages

Configuration checks report only whether a value is configured and whether its
classification is acceptable.

## Existing production-delivery boundary

v245 must not modify or weaken:

- The default-off feature gate.
- Double explicit production confirmation.
- Positive owner scoping.
- Explicit bounded production limits.
- Maximum production batch size of 25.
- Known nonproduction-backend rejection.
- Persistent delivery audit behavior.
- Sent-timestamp rollback protection.
- Per-item failure isolation.
- Sanitized production command output.
- The separate locmem-only test-send path.
- The nonautomatic scheduler boundary.

## Schema, UI and automation boundary

v244 and the proposed v245 implementation introduce no:

- Model change
- Migration
- Admin registration
- URL
- Template
- Browser UI
- Background worker
- Celery integration
- Cron configuration
- Startup execution
- Request-time readiness check
- Automatic delivery

The latest listings migration remains:

`0016_savedsearchnotificationauditevent`

Migration `0017` remains absent.

## Acceptance gate

v245 is accepted only when:

- The implementation remains within the exact four-file scope.
- Focused v244–v245 transition tests pass.
- Existing production-delivery safety tests pass.
- Default development configuration reports not-ready safely.
- A valid overridden production-like configuration reports ready.
- Strict mode fails closed for not-ready configuration.
- Non-strict mode remains read-only and report-only.
- Human and JSON outputs remain sanitized.
- No protected runtime or schema file changes.
- The complete regression suite remains green.

## Next checkpoint

v245: saved-search notification production delivery operational readiness implementation
