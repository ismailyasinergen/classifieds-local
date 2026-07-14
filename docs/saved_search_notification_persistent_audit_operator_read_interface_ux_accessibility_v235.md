# v235 — Saved-Search Notification Persistent Audit Operator UX and Accessibility Polish

## Checkpoint identity

- Base:
  `project-checkpoint-v234-saved-search-notification-persistent-audit-operator-read-interface-implementation`
- Target:
  `project-checkpoint-v235-saved-search-notification-persistent-audit-operator-read-interface-ux-accessibility-polish`
- Marker:
  `V235_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_UX_ACCESSIBILITY`

## Purpose

v235 improves the usability, keyboard accessibility, screen-reader structure,
filter clarity, and responsive behavior of the v234 staff-only persistent audit
interface.

It does not change filtering semantics, CSV behavior, database models, runtime
event creation, notification delivery, rollback execution, URLs, or Django
admin registration.

## View-context improvements

The staff view now exposes:

- Human-readable active-filter summaries.
- Per-filter removal URLs.
- Clear-all URL.
- Previous and next page URLs.
- Human-readable result summary.
- Bounded CSV URL.
- CSV truncation guidance.
- Stable UX marker.

Page and CSV query behavior remain delegated to the unchanged v234 query
service.

## Filter usability

Filters are grouped into accessible fieldsets:

1. Event identity.
2. Classification.
3. Correlation identifiers.
4. Date range and page size.

Every control has an explicit associated label.

Date inputs reference shared timezone-aware ISO-8601 guidance.

Invalid filters still fail closed with HTTP 400.

## Applied-filter clarity

The page displays active filters as removable chips.

Each chip:

- Shows a human-readable label.
- Shows a human-readable choice value.
- Removes only its own filter.
- Drops stale page state.
- Preserves other active filters.
- Has an accessible removal label.

A clear-all action remains available.

## Landmarks and navigation

The template adds:

- A skip link to the audit-event results.
- A stable main landmark.
- A labelled filter section.
- A labelled results section.
- A live result-count status.
- A labelled pagination navigation.
- `rel="prev"` and `rel="next"` links.
- Current-page semantics.

## Event-card accessibility

Each event card:

- Uses an article element.
- Is labelled by its own unique heading.
- Identifies outcome text for screen readers.
- Provides an accessible fingerprint copy button.
- Provides a polite copy-result status region.
- Labels the metadata region.
- Makes long metadata keyboard-scrollable.
- Preserves read-only rollback navigation.

## Keyboard and visual accessibility

The template includes:

- Strong `:focus-visible` outlines.
- Keyboard-operable buttons and links.
- A visually-hidden utility.
- Reduced-motion support.
- Forced-colors support.
- Responsive single-column behavior.
- High-contrast state badges.
- Mobile-width action controls.

## Empty state

Filtered empty results use a polite status region and provide a clear-filter
action.

The page explains that no matching persistent audit events were found without
suggesting a delivery, retry, rollback, or mutation action.

## CSV clarity

The page explains that CSV export:

- Uses the same filters and ordering.
- Is bounded to 5,000 rows.
- May truncate a larger result set.

The CSV endpoint and serialization remain unchanged.

## Preserved security and privacy boundaries

v235 does not expose:

- Owner email.
- Recipient email.
- Saved-search path.
- Saved-search query string.
- Saved-search query parameters.
- Email subject.
- Rendered email content.
- Exception messages.
- Tracebacks.
- Tokens, sessions, credentials, or secrets.

The metadata sanitizer remains unchanged.

## Preserved read-only boundary

The interface still:

- Accepts GET and HEAD only.
- Returns 405 for mutation methods.
- Redirects anonymous users to login.
- Returns 403 for authenticated non-staff users.
- Performs no audit-event mutation.
- Performs no saved-search mutation.
- Performs no delivery or rollback execution.

## Unchanged protected surfaces

v235 does not modify:

- Operator query and serialization service.
- URL configuration.
- Database models.
- Migration `0016`.
- Django admin.
- Persistence writer.
- Runtime adapter.
- Scheduler.
- Renderer.
- Sender.
- Rollback helper.
- Management command.
- Email settings.
- Production delivery safeguards.

## Acceptance gates

- Skip link reaches the result section.
- Form controls have associated labels.
- Filter groups have legends.
- Active-filter chips are human-readable.
- Removing one filter preserves the others.
- Pagination preserves filters.
- Result count is announced.
- Event cards have unique heading relationships.
- Fingerprint copying is keyboard-operable.
- Copy feedback is announced.
- Metadata is keyboard-scrollable and labelled.
- Empty state is announced.
- Focus-visible styling exists.
- Reduced-motion support exists.
- Forced-colors support exists.
- CSV behavior remains unchanged.
- Access control remains unchanged.
- No privacy regression occurs.
- No data mutation occurs.
- No model or migration change is generated.
- Runtime and admin remain unchanged.
- Full regression remains green.

## Next checkpoint

v236: saved-search notification persistent audit operator navigation integration contract
