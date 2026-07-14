# v239 — Saved-Search Notification Persistent Audit Operator Shared-Shell Integration Implementation

## Checkpoint identity

- Base:
  `project-checkpoint-v238-saved-search-notification-persistent-audit-operator-shared-shell-integration-contract`
- Target:
  `project-checkpoint-v239-saved-search-notification-persistent-audit-operator-shared-shell-integration-implementation`
- Marker:
  `V239_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_SHARED_SHELL_INTEGRATION`

## Purpose

v239 mounts the existing read-only saved-search notification audit operator
interface inside the project’s shared `base.html` shell.

The operator page now receives the common header, grouped Admin tools
navigation and shared document landmarks without changing its query, filter,
CSV, authorization or runtime behavior.

## Modified template

`backend/listings/templates/listings/saved_search_notification_audit_events.html`

The template now:

- Extends `base.html`.
- Uses the existing `content` block.
- No longer owns a doctype.
- No longer owns an `html` element.
- No longer owns a `head` element.
- No longer owns a `body` element.
- No longer introduces a second `main` landmark.

`backend/templates/base.html` remains unchanged.

## Main-content reconciliation

The former child:

`<main id="main-content">`

is replaced by a non-landmark wrapper:

`<div id="main-content" class="saved-search-audit-page">`

This preserves the historical `main-content` target while ensuring that the
only rendered `main` landmark is the shared one owned by `base.html`.

The former page-level `header` wrapper is represented by:

`<div data-v239-region="page-header">`

Its classes, attributes, heading content and targeted CSS behavior are
preserved. The `data-v239-region="page-header"` marker belongs only to this
single page-level wrapper. Repeated event-heading wrappers remain
`<div class="event-heading">` and do not reuse the page-header marker.

This also avoids the historical v238 raw-source check confusing `<header>`
with the forbidden document-level `<head>` element.

## Shared navigation

A staff request to:

`/staff/saved-search-notification-audit/`

now renders the shared Admin tools navigation.

The existing:

`Notification audit`

link is active and continues to render:

- `class="active"`
- `aria-current="page"`

The active state remains based on the resolver namespace and URL name, so query
parameters do not affect it.

## CSS isolation

The standalone page previously owned the entire document and could safely use
global selectors such as:

- `:root`
- `body`
- `main`
- `h1`
- `label`
- `input`
- `button`

Under the shared shell, those global selectors could affect the header or
navigation.

v239 scopes the existing operator CSS under:

`.saved-search-audit-page`

Root selectors are mapped to the page wrapper and all other page selectors are
prefixed with the wrapper scope.

Nested rules inside media, supports, layer, container and document blocks are
also scoped.

Keyframes and declaration-only at-rules are preserved without selector
rewriting.

## Preserved CSS behavior

The integration preserves:

- Existing CSS variables.
- Page background and panel styling.
- Responsive filter layout.
- Responsive event-card layout.
- Focus-visible styling.
- Reduced-motion behavior.
- Forced-colors behavior.
- Visually hidden utility behavior.
- Skip-link behavior.
- Keyboard-scrollable metadata styling.

No CSS framework, JavaScript framework, CDN or external asset is introduced.

## Preserved JavaScript

The existing fingerprint-copy script remains in the child content block.

It continues to provide:

- Keyboard-operable copy buttons.
- Clipboard API support.
- Fallback copy behavior.
- Successful-copy announcement.
- Failure announcement.
- Live copy-status updates.

No background process, network call or delivery action is added.

## Accessibility targets

The rendered page preserves:

- `href="#audit-events"`
- `id="main-content"`
- `id="audit-events"`
- `tabindex="-1"`
- `id="copy-status"`
- Live copy announcements.
- Filter fieldsets and legends.
- Explicit form labels.
- Result summary announcements.
- Event-heading relationships.

The rendered document now has one doctype, one `html`, one `head`, one `body`
and one `main`.

## Behavior preservation

v239 does not change:

- Exact filter parsing.
- Invalid-filter HTTP 400 behavior.
- Duplicate-filter fail-closed behavior.
- Active-filter chips.
- Per-filter removal URLs.
- Clear-all behavior.
- Bounded pagination.
- Filter-preserving pagination.
- Out-of-range page handling.
- Bounded CSV export.
- CSV formula-injection protection.
- Metadata sanitization.
- Empty-state guidance.
- Read-only rollback links.

## Authorization preservation

The destination continues to enforce:

- Anonymous request: login redirect.
- Authenticated non-staff request: HTTP 403.
- Staff request: HTTP 200.
- Superuser request: HTTP 200.
- POST, PUT, PATCH and DELETE: HTTP 405.

Navigation visibility is not treated as authorization.

## Privacy boundary

Shared-shell integration adds no:

- Owner email.
- Recipient email.
- Saved-search query text.
- Saved-search query parameters.
- Notification subject.
- Notification body.
- Raw private metadata.
- Secret or token.
- Operational count in navigation.

The existing sanitized operator read model remains authoritative.

## Read-only boundary

The integrated page adds no:

- POST form.
- Send action.
- Retry action.
- Rollback execution.
- Edit action.
- Delete action.
- Timestamp mutation.
- Automatic notification delivery.
- Background worker.
- Scheduler wiring.

The existing informational text explaining that the page cannot send or retry
delivery remains visible.

## Unchanged protected surfaces

v239 does not modify:

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
- Historical v234–v238 artifacts.

## Model and migration boundary

No model change is introduced.

No migration is introduced.

The latest listings migration remains:

`0016_savedsearchnotificationauditevent`

The audit-event model remains absent from editable Django admin.

## Acceptance gates

- Operator template extends `base.html`.
- Operator template uses the `content` block.
- Standalone document tags are removed.
- Child template introduces no nested `main`.
- CSS is isolated under the operator page wrapper.
- Page-specific JavaScript remains present.
- Shared Admin tools navigation renders.
- `Notification audit` is active.
- Active link uses `aria-current="page"`.
- Query parameters preserve the active state.
- Existing accessibility targets remain present.
- v234 read-interface tests remain green.
- v235 UX/accessibility tests remain green.
- v236 navigation contract tests remain green.
- v237 navigation implementation tests remain green.
- v238 shared-shell transition contract remains green.
- Authorization and GET-only behavior remain unchanged.
- No model, migration, admin, runtime or delivery change is introduced.
- Full regression remains green.

## Next checkpoint

v240: saved-search notification persistent audit operator shared-shell integration closeout audit
