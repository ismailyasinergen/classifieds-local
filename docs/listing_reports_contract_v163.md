# v163 Listing Reports Contract Checkpoint

LISTING_REPORTS_CONTRACT_V163

## Purpose

This checkpoint protects the `listing_reports` lane before and during extraction from `backend/listings/views.py`.

v162 identified `listing_reports` as the next safest extraction candidate after the CRUD/upload lane was moved in v161.

## Scope

The contract records and protects:

- current `listing_reports` definition counts,
- duplicate/shadowed report function names,
- active report function source footprint,
- existing listing-report URL route aliases,
- current callback identity through `listings.views`,
- existing listing report status UX coverage,
- trust-safety report event service wiring,
- moderation-notice creation paths.

## Protected report lane functions

The report lane includes:

- `moderation_queue`
- `listing_report_create`
- `listing_report_queue`
- `listing_report_export_csv`
- `my_listing_reports`
- `_safe_reporter_note`
- `listing_report_review`
- `listing_report_dismiss`
- `listing_report_suspend_listing`
- `listing_report_archive_listing`

## Protected route aliases

The existing public route names are:

- `listing_report` -> `listing_report_create`
- `report_queue` -> `listing_report_queue`
- `report_export_csv` -> `listing_report_export_csv`
- `my_reports` -> `my_listing_reports`
- `report_review` -> `listing_report_review`
- `report_dismiss` -> `listing_report_dismiss`
- `report_suspend_listing` -> `listing_report_suspend_listing`
- `report_archive_listing` -> `listing_report_archive_listing`

## v164 extraction follow-up

v164 extracts the protected listing report lane into `backend/listings/listing_reports_views.py`.

Compatibility remains available through `listings.views` re-exports, so URL configuration and callers can continue using the existing route aliases and `views.<callback>` references.

## Non-goals

- Do not change public route names.
- Do not change templates, permissions, models, migrations, or runtime behavior.
- Do not remove compatibility access through `listings.views`.

## Next safe step after v164

Prepare a contract checkpoint for the remaining `saved_searches` lane before moving any saved-search runtime code.
