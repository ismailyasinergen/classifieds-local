# v163 Listing Reports Contract Checkpoint

LISTING_REPORTS_CONTRACT_V163

## Purpose

This checkpoint protects the remaining `listing_reports` lane before any runtime code is moved out of `backend/listings/views.py`.

v162 identified `listing_reports` as the next safest extraction candidate after the CRUD/upload lane was moved in v161.

## Scope

v163 is a contract checkpoint only.

It records and protects:

- current `listing_reports` definition counts,
- duplicate/shadowed report function names,
- active report function source footprint,
- existing listing-report URL route aliases,
- current callback identity through `listings.views`,
- existing listing report status UX coverage,
- the v162 audit recommendation that `listing_reports` should be extracted before `saved_searches`.

## Protected report lane functions

The current report lane includes:

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

## Non-goals

- Do not move runtime code in v163.
- Do not create `listing_reports_views.py` in v163.
- Do not change URLs, permissions, templates, models, migrations, or runtime behavior.
- Do not remove compatibility access through `listings.views`.

## Next safe step

v164 should extract the protected listing report lane into a dedicated module, while preserving route callbacks and compatibility re-exports.
