# v237 — Saved-Search Notification Persistent Audit Operator Navigation Integration Implementation

## Checkpoint identity

- Base:
  `project-checkpoint-v236-saved-search-notification-persistent-audit-operator-navigation-integration-contract`
- Target:
  `project-checkpoint-v237-saved-search-notification-persistent-audit-operator-navigation-integration-implementation`
- Marker:
  `V237_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_NAVIGATION_INTEGRATION`

## Purpose

v237 exposes the existing read-only saved-search notification audit interface
through the existing grouped staff navigation.

## Navigation owner

Modified template:

`backend/templates/base.html`

Existing navigation marker:

`ADMIN_NAV_CLEANUP_V2`

Parent group:

`Admin tools`

## Placement

The new link is inserted immediately after the existing:

`Audit Tracking`

link.

Visible label:

`Notification audit`

Accessible label:

`Inspect saved-search notification audit events`

## Route

The navigation uses Django’s named route:

`listings:saved-search-notification-audit-events`

Resolved path:

`/staff/saved-search-notification-audit/`

The path is not hardcoded in `base.html`.

## Visibility

The link remains inside the existing staff-only Admin tools navigation.

It is visible to:

- Staff users.
- Superusers.

It is hidden from:

- Anonymous visitors.
- Authenticated non-staff users.
- Non-staff buyers.
- Non-staff sellers.

## Active state

The template compares:

- Resolver namespace: `listings`
- Resolver URL name:
  `saved-search-notification-audit-events`

When active, the link renders:

- `class="active"`
- `aria-current="page"`

Query parameters do not affect the active state.

## Accessibility

The link:

- Uses visible descriptive text.
- Includes an explicit accessible label.
- Is a standard keyboard-operable anchor.
- Uses `aria-current="page"` while active.
- Does not open a new browser window.
- Does not use a download attribute.
- Preserves the existing navigation focus order.

## Privacy and read-only boundary

The navigation renders no:

- Event count.
- Failure count.
- Pending count.
- Owner or recipient identifier.
- Correlation identifier.
- Event metadata.
- Notification content.
- Operational status badge.

It adds no send, retry, rollback, edit, delete or timestamp action.

## Authorization preservation

Target authorization remains unchanged:

- Anonymous requests redirect to login.
- Authenticated non-staff requests receive HTTP 403.
- Staff requests receive HTTP 200.
- POST, PUT, PATCH and DELETE receive HTTP 405.

Navigation visibility is not treated as authorization.

## Preserved navigation

v237 preserves:

- Admin tools grouping.
- Overview.
- Appeals.
- Listing Reports.
- Seller Reports.
- Action Log.
- Event Log.
- Audit Tracking.
- Existing buyer and seller navigation.
- Existing responsive navigation behavior.

## Protected surfaces

v237 does not modify:

- Operator query service.
- Operator view.
- Operator standalone page template.
- Listings URL configuration.
- Models.
- Migration `0016`.
- Django admin.
- Persistence writer.
- Runtime adapter.
- Renderer.
- Scheduler.
- Sender.
- Rollback helper.
- Management command.
- Core smoke test source.
- v236 contract artifacts.

## Model and migration boundary

No model change is introduced.

No migration is introduced.

The latest listings migration remains:

`0016_savedsearchnotificationauditevent`

The audit-event model remains absent from editable Django admin.

## Shared-shell follow-up

The operator page still uses its standalone v235 shell. The navigation link is
now available on shared-shell pages, and its active-state logic is ready.

A future checkpoint can integrate the operator page with the shared base
template without changing query, authorization or read-only behavior.

## Acceptance gates

- Exactly one Notification audit link is present.
- The link follows Audit Tracking.
- The link uses the existing named route.
- Staff and superusers see the link.
- Anonymous and non-staff users do not see the link.
- Active state uses `class="active"`.
- Active state uses `aria-current="page"`.
- Query parameters preserve active state.
- No hardcoded operator path is introduced.
- No count, private data or mutation action is introduced.
- Existing target authorization remains unchanged.
- Existing navigation tests remain green.
- v234–v236 transition tests remain green.
- No model or migration change is generated.
- Runtime and delivery surfaces remain unchanged.
- Full regression remains green.

## Next checkpoint

v238: saved-search notification persistent audit operator shared-shell integration contract
