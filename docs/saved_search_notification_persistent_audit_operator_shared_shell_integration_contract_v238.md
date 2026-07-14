# v238 — Saved-Search Notification Persistent Audit Operator Shared-Shell Integration Contract

## Checkpoint identity

- Base:
  `project-checkpoint-v237-saved-search-notification-persistent-audit-operator-navigation-integration-implementation`
- Target:
  `project-checkpoint-v238-saved-search-notification-persistent-audit-operator-shared-shell-integration-contract`
- Marker:
  `V238_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION_CONTRACT`

## Purpose

v238 defines the contract for mounting the existing saved-search notification
audit operator page inside the project’s shared `base.html` shell.

This checkpoint is contract-only. It does not modify the operator page,
navigation, view, query service, URL configuration, model or runtime.

## Current state

The project currently has two independent document shells:

1. `backend/templates/base.html`
   - Owns the common HTML document.
   - Owns the shared header and navigation.
   - Contains the v237 `Notification audit` navigation link.
   - Exposes the Django `content` block.

2. `backend/listings/templates/listings/saved_search_notification_audit_events.html`
   - Owns a separate doctype, `html`, `head` and `body`.
   - Owns page-specific CSS and JavaScript.
   - Does not currently extend `base.html`.
   - Therefore does not display the shared Admin tools navigation.

## v239 implementation scope

v239 may change exactly:

1. `backend/listings/templates/listings/saved_search_notification_audit_events.html`
2. `backend/listings/test_saved_search_notification_persistent_audit_operator_shared_shell_integration_v239.py`
3. `docs/saved_search_notification_persistent_audit_operator_shared_shell_integration_v239.md`

`backend/templates/base.html` must remain unchanged.

The existing `content` block is sufficient for shared-shell integration.
Optional base blocks may be reused only when they already exist; v239 must not
add new extension points to `base.html`.

## Template inheritance contract

The operator template must:

- Extend `base.html`.
- Define its page content through the `content` block.
- Stop owning its own doctype.
- Stop owning its own `html` element.
- Stop owning its own `head` element.
- Stop owning its own `body` element.
- Avoid adding a nested `main` landmark inside the shared base `main`.
- Preserve page-specific CSS and JavaScript without adding an external
  frontend dependency.

## Navigation contract

After integration, a staff request to:

`/staff/saved-search-notification-audit/`

must render the shared Admin tools navigation.

The link:

`Notification audit`

must be active and must retain:

- `class="active"`
- `aria-current="page"`

The link must remain staff-only and must continue to use:

`listings:saved-search-notification-audit-events`

## Accessibility reconciliation

The standalone page currently exposes:

- `href="#audit-events"`
- `id="main-content"`
- `id="audit-events"`
- `tabindex="-1"`

v239 must preserve these rendered accessibility targets so all v235
accessibility tests remain green.

The child template must not introduce a second `main` landmark. The
`main-content` identifier may be retained on a non-`main` content container
inside the shared shell.

The final rendered page must have:

- One shared document shell.
- No nested `main` landmark.
- A working skip target.
- The existing filter and result landmarks.
- Active-navigation semantics.

## Behavior preservation

Shared-shell integration must not change:

- Staff-only HTML access.
- Anonymous login redirect.
- Authenticated non-staff HTTP 403.
- GET and HEAD method restriction.
- Exact filter parsing.
- Fail-closed invalid-filter behavior.
- Active-filter chips.
- Filter-removal links.
- Bounded pagination.
- Filter-preserving pagination.
- Bounded CSV export.
- CSV formula-injection protection.
- Metadata re-sanitization.
- Fingerprint copy control.
- Copy-status live announcement.
- Empty-state guidance.
- Read-only rollback navigation.

## Style and script preservation

v239 must preserve:

- Existing page-specific visual hierarchy.
- Focus-visible styling.
- Reduced-motion behavior.
- Forced-colors behavior.
- Responsive filter and event-card layout.
- Keyboard-scrollable metadata regions.
- Fingerprint copy behavior.
- Clipboard fallback behavior.
- Live copy status.

No new JavaScript framework, CSS framework, CDN or external asset is allowed.

## Privacy boundary

Shared-shell integration must not expose:

- Owner email.
- Saved-search query text.
- Recipient email.
- Notification body.
- Raw private metadata.
- Delivery secrets.
- New audit-event counts in navigation.

The existing sanitized operator read model remains authoritative.

## Read-only boundary

The integrated page must remain navigation and inspection only.

It must not add:

- POST forms.
- Retry actions.
- Send actions.
- Rollback execution.
- Edit actions.
- Delete actions.
- Timestamp changes.
- Background processing.
- Automatic delivery.

## Protected surfaces

v239 must not modify:

- `backend/templates/base.html`
- Operator query service.
- Operator view.
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
- Core navigation smoke tests.
- v234–v238 historical test and document artifacts.

## Model and migration boundary

No model change is required.

No migration is required.

The latest listings migration remains:

`0016_savedsearchnotificationauditevent`

The audit-event model remains absent from editable Django admin.

## Transition compatibility

The v238 contract tests support two valid states:

1. Deferred state:
   - Operator page still owns its standalone shell.
   - v239 marker and artifacts do not exist.

2. Packaged state:
   - Operator page extends `base.html`.
   - Standalone document tags are removed.
   - v239 marker, test and document exist.

This allows the v238 transition contract to remain green when v239 is
implemented.

## v239 acceptance gates

- Operator template extends `base.html`.
- Operator template uses the `content` block.
- Child doctype, `html`, `head` and `body` tags are removed.
- Child template does not add a nested `main`.
- Shared Admin tools navigation renders on the operator page.
- `Notification audit` is active.
- Active link includes `aria-current="page"`.
- Existing accessibility targets remain present.
- v234 read-interface tests remain green.
- v235 UX and accessibility tests remain green.
- v236 navigation contract tests remain green.
- v237 navigation implementation tests remain green.
- Filter, pagination, CSV, metadata and copy behavior remain green.
- Authorization and GET-only behavior remain unchanged.
- No model, migration, admin, runtime or delivery change is introduced.
- Full regression remains green.

## Next checkpoint

v239: saved-search notification persistent audit operator shared-shell integration implementation
