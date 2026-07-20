# v304 — Notification delivery policy baseline

## Purpose

v304 defines one executable repository contract for four notification-delivery
policy gaps:

- verified-recipient state;
- provider delivery, bounce and complaint outcomes;
- notification-delivery-event retention;
- recipient data in operator output.

The milestone does not implement those capabilities. It makes their current
state, required prerequisites and fail-safe defaults machine-readable without
changing delivery behavior.

## Executable policy surface

The policy module is:

    listings.notification_delivery_policy_v304

The read-only management command is:

    python manage.py check_notification_delivery_policy

Structured output is available through:

    python manage.py check_notification_delivery_policy --json

Strict mode exits non-zero while blocking implementation capabilities are
missing:

    python manage.py check_notification_delivery_policy --strict

The default text and JSON results contain no recipient address values.

## Current repository result

The current baseline reports:

- policy defined: true;
- read only: true;
- mutation allowed: false;
- delivery attempted: false;
- provider accessed: false;
- runtime enforcement ready: false;
- runtime enforcement enabled: false;
- one ready current-runtime guardrail;
- four blocking policy capabilities not ready.

The established delivery guardrails remain active:

- a non-empty configured account email;
- explicit notification preferences;
- durable logical-event deduplication;
- atomic claims and bounded retry handling.

## Verified-recipient contract

Current state:

- no repository-visible email-specific verification field;
- no verification workflow bound to the current address;
- no verification provenance or timestamp contract.

Required before enforcement readiness:

- persisted state bound to the exact current email address;
- verified-at semantics;
- invalidation when the address changes;
- secure verification workflow and replay protection;
- opt-in, unsubscribe and privacy validation.

Safe default:

- do not describe the address as verified;
- do not silently enable verified-recipient enforcement;
- preserve the current non-empty-email behavior until the lifecycle is defined.

## Provider-outcome contract

Current state:

- synchronous backend exceptions are recorded;
- zero-delivery backend results are recorded;
- no provider message identifier exists;
- no authenticated provider webhook exists;
- no bounce or complaint ingestion exists.

Required before readiness:

- provider message identity;
- authenticated and replay-safe webhook ingestion;
- idempotent provider-event identity;
- bounce and complaint classifications;
- ownership validation and redacted logs;
- a defined interaction with retry and suppression policy.

Safe default:

- backend acceptance must not be described as confirmed provider delivery.

## Retention contract

Current state:

- notification delivery events are durable;
- no automatic age-based deletion runs;
- no approved retention duration is configured.

Required before readiness:

- a positive approved retention duration;
- legal-hold behavior where applicable;
- backup and restore handling;
- deletion evidence and audit behavior;
- age-boundary and query-plan validation.

Safe default:

- no destructive cleanup is permitted.

## Operator recipient-output contract

Target policy:

    redacted_by_default

The v304 inventory identifies four legacy output surfaces:

- explicit saved-search email-send results;
- saved-search email preview output;
- saved-search observability samples;
- saved-search rollback and audit output.

v304 does not rewrite those existing contracts. Their migration must be
performed together with updated command snapshots and troubleshooting guidance.

Safe default:

- add no new raw-recipient operator output;
- keep the new policy command fully sanitized;
- do not weaken legacy contracts partially or silently.

## Strict-mode meaning

Strict mode does not mean that the application is unsafe to run under its
existing behavior. It means the four future policy capabilities are not yet
ready for enforcement or automation.

Strict mode is intended for future release gates that explicitly require all
four capabilities.

## Deliberate exclusions

v304 adds no:

- model or schema migration;
- route, view, template or admin surface;
- email verification workflow;
- provider client or webhook;
- provider network access;
- bounce or complaint suppression;
- event deletion or archival job;
- background worker;
- sender enforcement;
- legacy operator-output rewrite;
- application or development-database mutation.

## Validation evidence

The completed v304 validation recorded:

- 12 focused policy tests passing;
- 49 related v287, v288 and v301 notification compatibility tests passing;
- text and JSON command output remaining recipient-sanitized;
- strict mode failing while required capabilities are missing;
- strict mode passing for a fully ready mocked contract;
- Python compilation passing;
- Django system checks reporting zero issues;
- `makemigrations --check --dry-run` reporting no changes;
- `migrate --check --noinput` passing against the development database;
- AST validation confirming no delivery or mutation calls in the policy module;
- all four preserved PostgreSQL worker clones refreshed from the migrated base;
- the complete parallel regression discovering and running 2,685 tests;
- explicit full-suite `OK` in 358.564 seconds;
- 379 seconds measured wall-clock time;
- no `FAILED` summary;
- the exact six-file v304 scope remaining intact and unstaged;
- the listings migration head remaining
  `0023_listingpricehistory_discount_guardrail_v293`.

v304 did not run `migrate` against the development database. It adds no model,
schema migration, route, provider integration, background worker, delivery
enforcement, retention deletion or legacy operator-output rewrite.
