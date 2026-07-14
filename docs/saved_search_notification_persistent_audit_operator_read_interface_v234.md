# v234 — Saved-Search Notification Persistent Audit Operator Read Interface

## Checkpoint identity

- Base:
  `project-checkpoint-v233-saved-search-notification-persistent-audit-operator-read-interface-contract`
- Target:
  `project-checkpoint-v234-saved-search-notification-persistent-audit-operator-read-interface-implementation`
- Marker:
  `V234_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_READ_INTERFACE`

## Purpose

v234 implements the v233 staff-only, read-only interface for persistent
`SavedSearchNotificationAuditEvent` records.

The implementation adds:

- Strict filter parsing.
- Deterministic queryset construction.
- Privacy-minimized serialization.
- Recursive metadata read sanitization.
- Bounded HTML pagination.
- Bounded CSV export.
- A dedicated staff-only view.
- A dedicated staff URL.
- A read-only HTML template.

## Route

Path:

`staff/saved-search-notification-audit/`

URL name:

`saved-search-notification-audit-events`

The route is inserted before broader listing routes so that catch-all patterns
cannot intercept it.

## Authorization

Anonymous requests redirect to the configured login page.

Authenticated users without `is_staff=True` receive HTTP 403.

The view accepts:

- `GET`
- `HEAD`

Mutation methods return HTTP 405.

## Query service

Module:

`listings.saved_search_notification_audit_operator`

Public API:

- `SavedSearchNotificationAuditOperatorFilters`
- `SavedSearchNotificationAuditOperatorPage`
- `parse_saved_search_notification_audit_operator_filters`
- `build_saved_search_notification_audit_operator_queryset`
- `serialize_saved_search_notification_audit_event_for_operator`
- `sanitize_saved_search_notification_audit_metadata_for_operator`
- `iter_saved_search_notification_audit_csv_rows`

## Strict filter handling

Supported filters:

- Event ID.
- Saved-search ID.
- Owner ID snapshot.
- Event type.
- Outcome.
- Actor type.
- Source.
- Reason code.
- Batch ID.
- Correlation ID.
- Delivery-attempt ID.
- Idempotency key.
- Notification fingerprint.
- Rollback linkage.
- Occurred-from timestamp.
- Occurred-to timestamp.
- Page.
- Page size.
- Output format.

Invalid, duplicate, unsupported, oversized, naive-datetime, or reversed-range
filters return HTTP 400.

Filters are not silently ignored.

## Query ordering and bounds

Ordering:

1. `occurred_at` descending.
2. `created_at` descending.
3. Event UUID descending.

HTML:

- Default page size: 50.
- Maximum page size: 100.
- Out-of-range pages return HTTP 400.

CSV:

- Maximum rows: 5,000.
- Export truncation is declared through response headers.
- The same filters and ordering are used for HTML and CSV.

## Privacy

The query service selects the saved search only for its ID and display name.

It does not select the owner relation.

The interface does not expose:

- Owner email.
- Recipient email.
- Saved-search path.
- Saved-search query string.
- Saved-search query parameters.
- Email subject.
- Rendered email content.
- Listing titles or descriptions.
- Private URLs.
- Exception messages.
- Tracebacks.
- Credentials, cookies, sessions, or tokens.

## Metadata read sanitization

Stored metadata is sanitized again during read.

The sanitizer:

- Processes nested objects and arrays.
- Ignores non-string keys.
- Redacts sensitive-key values.
- Limits traversal depth to six levels.
- Limits long string values.
- Produces canonical sorted JSON.
- Replaces oversized JSON output with a bounded truncation record.

Maximum rendered metadata size:

16 KiB.

Redaction text:

`[redacted]`

## CSV safety

CSV output has a fixed header set.

Cells beginning with:

- `=`
- `+`
- `-`
- `@`

receive a leading single quote.

This neutralizes spreadsheet formula interpretation.

## Rollback links

Rollback relationships link back to the same read-only interface through the
target event UUID.

No rollback preview, execution, timestamp restoration, delivery, resend, or
retry action exists on the page.

## Read-only boundary

The operator modules do not import:

- Runtime event recorder.
- Persistence writer.
- Scheduler.
- Sender.
- Rollback executor.

The interface performs no event or saved-search mutation.

## Unchanged surfaces

v234 does not modify:

- `SavedSearchNotificationAuditEvent` model.
- Migration `0016`.
- Django admin registration.
- Runtime adapter.
- Persistence writer.
- Scheduler.
- Renderer.
- Sender.
- Rollback helper.
- Management command.
- Notification templates.
- Email settings.
- Production-delivery safeguards.

## Acceptance gates

- Anonymous access redirects to login.
- Authenticated non-staff access returns 403.
- Mutation methods return 405.
- Staff HTML access works.
- Staff CSV access works.
- Invalid filters return 400.
- Exact filters return exact records.
- Pagination is deterministic and bounded.
- CSV is bounded.
- CSV formula injection is neutralized.
- Metadata is sanitized on read.
- Private owner and notification data are not exposed.
- Rollback links remain navigational.
- HTML and CSV requests do not mutate data.
- Audit model remains admin-unregistered.
- No model or migration change is generated.
- Runtime integration remains unchanged.
- Full regression remains green.

## Next checkpoint

v235: saved-search notification persistent audit operator read-interface UX and accessibility polish
