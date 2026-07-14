# v236 — Saved-Search Notification Persistent Audit Operator Navigation Integration Contract

## Checkpoint identity

- Base:
  `project-checkpoint-v235-saved-search-notification-persistent-audit-operator-read-interface-ux-accessibility-polish`
- Target:
  `project-checkpoint-v236-saved-search-notification-persistent-audit-operator-navigation-integration-contract`
- Marker:
  `V236_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_NAVIGATION_INTEGRATION_CONTRACT`
- Next:
  `v237: saved-search notification persistent audit operator navigation integration implementation`

## Purpose

v236 defines how the existing staff-only persistent notification audit page
will be exposed through the existing grouped administration navigation.

This checkpoint is contract-only.

It does not add the navigation link.

## Existing navigation owner

The repository’s grouped administration navigation owner was discovered
fail-closed as:

`backend/templates/base.html`

v237 modifies this existing template rather than creating a second competing
administration navigation system.

## Destination

Named URL:

`listings:saved-search-notification-audit-events`

Resolved path:

`/staff/saved-search-notification-audit/`

Visible label:

`Notification audit`

Supporting description:

`Inspect saved-search notification audit events`

The navigation template must use Django’s named URL tag.

The route must not be hardcoded.

## Placement

The link belongs inside the existing:

`Admin tools`

administration group.

v237 must not create:

- A new top-level administration group.
- A second Admin tools group.
- A duplicate audit link.
- A public navigation item.
- A buyer navigation item.
- A seller navigation item.

The link should follow the existing operational Admin tools links without
reordering or removing them.

## Visibility

The link is visible when:

- The user is authenticated.
- `user.is_staff` is true.

The link is hidden for:

- Anonymous users.
- Authenticated non-staff users.
- Buyers without staff status.
- Sellers without staff status.

Superusers see the link because they are staff.

Navigation visibility is not a replacement for target-view authorization.

## Authorization preservation

The destination continues to enforce its own access rules:

- Anonymous direct requests redirect to login.
- Authenticated non-staff direct requests receive HTTP 403.
- Staff direct requests may access the read-only page.
- Mutation methods remain unavailable.

A hidden navigation link must never be treated as an authorization boundary.

## Active state

The link is active when the current resolved route has:

- Namespace: `listings`
- URL name: `saved-search-notification-audit-events`

The active state is independent of query parameters.

It remains active for:

- Default HTML results.
- Filtered HTML results.
- Paginated HTML results.

The active link uses:

`aria-current="page"`

A visual active class may also be used, but color alone must not communicate
the active state.

## Accessibility

The implementation must preserve the existing grouped-navigation semantics.

The link must:

- Have visible descriptive text.
- Be keyboard-operable.
- Participate in the existing focus order.
- Use the existing mobile navigation behavior.
- Avoid icon-only presentation.
- Avoid opening a new browser window.
- Avoid a download attribute.
- Expose `aria-current="page"` when active.

## Privacy

The navigation item is static.

It must not display:

- Audit-event counts.
- Failure counts.
- Pending counts.
- Owner identifiers.
- Recipient identifiers.
- Correlation identifiers.
- Event metadata.
- Notification content.
- Delivery state badges.

Displaying operational counts would create unnecessary database queries and
privacy exposure in a global navigation surface.

## Read-only boundary

The navigation item performs a normal GET request.

It must not expose:

- Send action.
- Retry action.
- Rollback action.
- Timestamp mutation.
- Event deletion.
- Event editing.
- Admin action.
- Background execution.

## Existing navigation preservation

v237 must preserve:

- Existing grouped administration navigation.
- Existing Admin tools links.
- Existing administration dashboard link.
- Existing moderation links.
- Existing report links.
- Existing action-log links.
- Existing buyer navigation.
- Existing seller navigation.
- Existing responsive/mobile behavior.
- Existing keyboard behavior.

## v237 implementation scope

Modify:

- `backend/templates/base.html`

Create:

- `backend/listings/test_saved_search_notification_persistent_audit_operator_navigation_integration_v237.py`
- `docs/saved_search_notification_persistent_audit_operator_navigation_integration_v237.md`

No other file is required by the contract.

## Protected surfaces

v237 must not modify:

- Operator query service.
- Operator view.
- Operator audit-page template.
- Listings URL configuration.
- Models.
- Migration `0016`.
- Django admin registration.
- Persistence writer.
- Runtime adapter.
- Renderer.
- Scheduler.
- Sender.
- Rollback helper.
- Management command.
- Email settings.
- Production-delivery safeguards.

## Model and migration boundary

No model field changes are required.

No migration is required.

The latest listings migration remains:

`0016_savedsearchnotificationauditevent`

The audit model remains absent from editable Django admin.

## Acceptance gates for v237

- Exactly one staff navigation link is rendered.
- Anonymous users do not see the link.
- Authenticated non-staff users do not see the link.
- Staff users see the link.
- The named URL resolves correctly.
- The link is inside the existing Admin tools group.
- Existing group links and ordering remain intact.
- Active state uses `aria-current="page"`.
- Filter and pagination query parameters preserve active state.
- No count or status badge is added.
- No private audit data appears in navigation.
- Target authorization remains unchanged.
- Existing core navigation smoke tests pass.
- v234 read-interface tests pass.
- v235 UX/accessibility tests pass.
- No model or migration change is generated.
- Runtime and delivery surfaces remain unchanged.
- Full regression remains green.

## Explicit exclusions

v236 does not:

- Modify navigation.
- Add a link.
- Add a new menu group.
- Modify the audit page.
- Modify URLs.
- Modify views.
- Modify query behavior.
- Add model permissions.
- Register the audit model in admin.
- Add event counts.
- Add delivery controls.
- Add rollback controls.
- Add a migration.
- Create `backend/docs`.

## Next checkpoint

v237: saved-search notification persistent audit operator navigation integration implementation
