# v164 Listing Reports View Extraction

LISTING_REPORTS_VIEW_EXTRACTION_V164

## Summary

v164 extracts the protected listing report lane from `backend/listings/views.py` into:

- `backend/listings/listing_reports_views.py`

Compatibility is preserved through `listings.views` re-exports.

## Preserved public route aliases

The existing URL names remain unchanged:

- `listing_report`
- `report_queue`
- `report_export_csv`
- `my_reports`
- `report_review`
- `report_dismiss`
- `report_suspend_listing`
- `report_archive_listing`

## Preserved callbacks

The following callbacks remain accessible through `listings.views`:

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

## Runtime behavior

No runtime behavior should change in v164.

The extraction preserves:

- duplicate/shadowed historical report definitions inside the dedicated module,
- active report callback identity through `listings.views`,
- listing report status UX behavior,
- moderation notice creation,
- trust-safety event service wiring,
- listing-level suspend/archive actions.

## Next safe step

The v162 audit now recommends `saved_searches` as the next remaining extraction lane.

## v174 follow-up

v174 removed only `SidebarCategoriesMixin` and `_safe_reporter_note` from the `listings.views` compatibility facade after the v173 targeted-removal contract proved zero facade dependency records for those two names.

The source modules still define/export their original objects. All non-target facade compatibility exports remain protected.
