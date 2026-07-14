# v233 — Saved-Search Notification Persistent Audit Operator Read-Interface Contract

## Checkpoint identity

- Base:
  `project-checkpoint-v232-saved-search-notification-audit-runtime-integration-implementation`
- Target:
  `project-checkpoint-v233-saved-search-notification-persistent-audit-operator-read-interface-contract`
- Marker:
  `V233_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_READ_INTERFACE_CONTRACT`
- Next implementation:
  `v234: saved-search notification persistent audit operator read-interface implementation`

## Purpose

v233 defines a staff-only, read-only interface for inspecting persisted
`SavedSearchNotificationAuditEvent` records.

This checkpoint is contract-only.

It does not create the query service, view, URL, template, CSV export, admin
registration, action, form, migration, or runtime modification.

## Relationship to existing operator surfaces

The existing v223 observability report continues to summarize current
`SavedSearch` readiness and timestamp state.

The existing v226 `SavedSearch` Django admin continues to expose read-only
notification status and preference controls.

The proposed persistent-audit interface is separate from both surfaces.

It inspects append-only historical audit events rather than current
saved-search readiness.

## Proposed implementation files

### Query and serialization service

`listings/saved_search_notification_audit_operator.py`

### Staff-only view

`listings/saved_search_notification_audit_operator_views.py`

### Template

`listings/templates/listings/saved_search_notification_audit_events.html`

### Existing URL configuration to update

`listings/urls.py`

### Route

Path:

`staff/saved-search-notification-audit/`

Name:

`saved-search-notification-audit-events`

### Output formats

- HTML by default.
- CSV through `?format=csv`.

Both formats use identical validated filters and deterministic ordering.

## Proposed public API

### Filter dataclass

`SavedSearchNotificationAuditOperatorFilters`

### Page result dataclass

`SavedSearchNotificationAuditOperatorPage`

### Filter parser

`parse_saved_search_notification_audit_operator_filters`

### Query builder

`build_saved_search_notification_audit_operator_queryset`

### Event serializer

`serialize_saved_search_notification_audit_event_for_operator`

### Metadata sanitizer

`sanitize_saved_search_notification_audit_metadata_for_operator`

### CSV iterator

`iter_saved_search_notification_audit_csv_rows`

### View

`SavedSearchNotificationAuditEventListView`

## Authorization

The interface requires:

- An authenticated user.
- `is_staff=True`.

Expected responses:

- Anonymous request: login redirect.
- Authenticated non-staff request: HTTP 403.
- Staff request: HTTP 200.

Allowed methods:

- `GET`
- `HEAD`

Forbidden methods:

- `POST`
- `PUT`
- `PATCH`
- `DELETE`

Forbidden methods return HTTP 405.

The interface exposes no object mutation endpoint.

## Event filters

### Event identity

- `event_id`
- `saved_search_id`
- `owner_id_snapshot`

### Event classification

- `event_type`
- `outcome`
- `actor_type`
- `source`
- `reason_code`

### Correlation identity

- `batch_id`
- `correlation_id`
- `delivery_attempt_id`
- `idempotency_key`
- `notification_fingerprint`

### Rollback linkage

- `rollback_linked`

### Date range

- `occurred_from`
- `occurred_to`

Date inputs must be timezone-aware ISO-8601 values.

### Pagination and output

- `page`
- `page_size`
- `format`

All identifiers use exact matching.

The interface does not provide an unbounded fuzzy search over the audit table.

## Validation behavior

Invalid input fails closed.

The following produce HTTP 400:

- Invalid choice.
- Invalid UUID.
- Invalid fingerprint.
- Invalid datetime.
- Naive datetime.
- Reversed date range.
- Invalid page number.
- Invalid page size.
- Page size above the maximum.
- Unsupported output format.

Invalid filters must not be silently ignored.

## Query behavior

Model:

`SavedSearchNotificationAuditEvent`

Related data:

- `saved_search` may be selected for its ID and display label.
- `saved_search__user` must not be selected.

Ordering:

1. `occurred_at` descending.
2. `created_at` descending.
3. Event UUID descending.

HTML pagination:

- Default page size: 50.
- Maximum page size: 100.

CSV export:

- Maximum rows: 5,000.
- Unbounded export is forbidden.

## HTML summary fields

- Event ID.
- Occurred timestamp.
- Saved-search ID.
- Saved-search label.
- Owner ID snapshot.
- Event type.
- Outcome.
- Reason code.
- Source.
- Actor type.
- Correlation ID.
- Delivery-attempt ID.
- Rollback target ID.

## HTML detail fields

- Created timestamp.
- Batch ID.
- Idempotency key.
- Notification fingerprint.
- Actor identifier.
- Checked timestamp before and after.
- Sent timestamp before and after.
- Sanitized metadata.

## Privacy boundary

The interface must never expose:

- Owner email.
- Recipient email.
- Saved-search query parameters.
- Saved-search query string.
- Saved-search path.
- Email subject.
- Rendered email HTML.
- Rendered email text.
- Listing titles.
- Listing descriptions.
- Private listing URLs.
- Raw exception messages.
- Tracebacks.
- Stack traces.
- Authorization values.
- Cookies.
- Sessions.
- Tokens.
- Passwords.
- Secrets.
- Credentials.

The owner identifier exposed by the interface is the immutable
`owner_id_snapshot`, not live account contact data.

## Metadata read sanitization

Persisted metadata is not trusted blindly merely because it passed the write
service.

The read interface sanitizes metadata recursively.

Requirements:

- String keys only.
- Sensitive keys are redacted.
- Canonical sorted JSON output.
- Maximum depth: 6.
- Maximum rendered size: 16 KiB.
- Oversized content is safely truncated.
- Redaction text: `[redacted]`.
- Template output is escaped.

## Fingerprint presentation

The HTML table displays a shortened fingerprint for readability.

The complete fingerprint remains available as an explicit copy value and in
bounded CSV export.

The fingerprint is an operational identifier, not rendered email content.

## Rollback linkage

Rollback events display their `rollback_of` relationship.

The link navigates to the same interface with:

`event_id=<target UUID>`

The link is read-only.

The persistent audit interface provides no:

- Rollback preview button.
- Rollback execution button.
- Timestamp restoration action.
- Delivery action.
- Retry action.

Missing rollback targets must not crash the interface.

## CSV contract

Filename:

`saved-search-notification-audit.csv`

Content type:

`text/csv; charset=utf-8`

CSV output:

- Uses the same validated filters as HTML.
- Uses the same deterministic ordering as HTML.
- Is capped at 5,000 rows.
- Uses UTC ISO-8601 timestamps.
- Includes a fixed header set.
- Includes canonical sanitized metadata JSON.
- Excludes private fields.
- Does not include recipient or owner email.
- Does not include saved-search query details.
- Does not include rendered content.

### Formula-injection protection

Cells beginning with any of the following are escaped:

- `=`
- `+`
- `-`
- `@`

The escape prefix is a single quote.

## Read-only invariants

The implementation must not:

- Create audit events.
- Save audit events.
- Update audit events.
- Delete audit events.
- Bulk-update audit events.
- Mutate saved searches.
- Change notification timestamps.
- Deliver email.
- Render or resend email.
- Invoke scheduler execution.
- Invoke rollback execution.
- Import the runtime recorder.
- Import the persistence writer.
- Register the audit model in editable Django admin.
- Add Django admin actions.
- Add retention deletion.
- Add a background worker.
- Add a retry worker.

## Django admin boundary

`SavedSearchNotificationAuditEvent` remains absent from
`admin.site._registry`.

The existing `SavedSearch` admin configuration remains unchanged.

The new interface is a dedicated staff page rather than an editable model
admin.

## Model and migration boundary

v233 adds no model fields.

v233 creates no migration.

The latest listings migration remains:

`0016_savedsearchnotificationauditevent`

The append-only model protections remain unchanged.

## Runtime boundary

v233 does not modify:

- Runtime audit adapter.
- Persistence writer.
- Scheduler.
- Renderer.
- Sender.
- Rollback helper.
- Management command.
- Notification templates.
- Email settings.
- Production-delivery safeguards.

## Existing surfaces preserved

v234 must preserve:

- v223 read-only observability reporting.
- v226 `SavedSearch` admin UX.
- v230 replay-safe persistence.
- v232 runtime event creation.
- Test-backend delivery gates.
- Default non-delivery command behavior.
- Production-delivery restrictions.
- Rollback transaction safeguards.

## Acceptance gates for v234

- Staff authentication is required.
- Authenticated non-staff users receive HTTP 403.
- Mutation methods receive HTTP 405.
- All filters are explicitly validated.
- Invalid filters return HTTP 400.
- Ordering is deterministic.
- HTML pagination is bounded.
- CSV export is bounded.
- CSV and HTML share filters and ordering.
- CSV formula injection is neutralized.
- Owner and recipient emails are never exposed.
- Saved-search query details are never exposed.
- Rendered email content is never exposed.
- Metadata is sanitized again on read.
- Values are template-escaped.
- Rollback links are navigational only.
- No delivery or rollback action exists.
- No timestamp mutation is possible.
- Audit model remains admin-unregistered.
- Existing `SavedSearch` admin remains unchanged.
- No model or migration change is generated.
- Existing runtime integration remains unchanged.
- Existing observability tests remain green.
- Existing admin UX tests remain green.
- Full regression remains green.

## Explicit exclusions

v233 does not:

- Create implementation modules.
- Add a URL.
- Add a view.
- Add a template.
- Add CSV export.
- Register the audit model in admin.
- Add delivery actions.
- Add retry actions.
- Add rollback actions.
- Add retention deletion.
- Modify runtime code.
- Modify the management command.
- Modify models.
- Create migration `0017`.
- Create `backend/docs`.

## Next checkpoint

v234: saved-search notification persistent audit operator read-interface implementation
