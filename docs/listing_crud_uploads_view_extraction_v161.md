# v161 Listing CRUD Uploads View Extraction

LISTING_CRUD_UPLOADS_VIEW_EXTRACTION_V161

## Purpose

v161 extracts the final tracked split lane, `listing_crud_uploads`, from `backend/listings/views.py` into `backend/listings/listing_crud_uploads_views.py`.

## Extracted module

- New module: `backend/listings/listing_crud_uploads_views.py`
- Compatibility path: `listings.views`
- Exports:
  - `ListingCreateView`
  - `ListingUpdateView`
  - `ListingDeleteView`
  - `listing_image_delete`
  - `listing_feature_days_update`

## Occurrence-based extraction

This lane is occurrence-based because it has duplicate/shadowed top-level class definitions.

Locked v160 occurrences:

- `ListingCreateView` (class), lines 52-84, line count 33
- `ListingUpdateView` (class), lines 87-126, line count 40
- `ListingDeleteView` (class), lines 129-143, line count 15
- `listing_image_delete` (function), lines 148-161, line count 14
- `listing_feature_days_update` (function), lines 241-261, line count 21
- `ListingCreateView` (class), lines 1152-1162, line count 11
- `ListingUpdateView` (class), lines 1166-1176, line count 11

## Locked footprint

- Definition occurrences: `7`
- Audit body-line footprint: `145`
- Decorator-inclusive source span: `149`

## Final split-lane state

After v161, all tracked split lanes are extracted:

- `browse_search_detail`
- `favorites`
- `listing_crud_uploads`
- `listing_promotions`
- `uncategorized`

There are no remaining tracked split-lane candidates.

## Non-goals

- Do not change URL routes.
- Do not change templates.
- Do not change permissions.
- Do not change models or migrations.
- Do not change runtime behavior beyond moving source definitions and preserving compatibility re-exports.

## Repair 1 import-order and Docker test-path follow-up

The `listings.views` compatibility re-export for `listing_crud_uploads_views` must appear before existing top-level aliases such as `_ReportOriginalListingCreateView = ListingCreateView`.

Repair 1 moves the re-export block near the top of `views.py` and keeps Docker tests from directly reading repo-root `docs/` files.

## Repair 2 internal alias dependency follow-up

The active duplicate/shadowed `ListingCreateView` and `ListingUpdateView` classes inherit from `_ReportOriginalListingCreateView` and `_ReportOriginalListingUpdateView`.

Repair 2 preserves those aliases inside `listing_crud_uploads_views.py` after the first/base create-update classes and before the later active duplicate classes.

## Repair 3 completed split-lane follow-up

After `listing_crud_uploads` is extracted, all tracked split lanes are complete. The follow-up audit records `recommended_next_lane = None` and documents the completed state as `none`.

## Repair 4 completed split-lane finalization

The follow-up audit no longer raises when all tracked split lanes are complete. The completed split state is represented by no remaining candidates and no recommended next lane.


## Repair 6 completed-state compatibility alignment

Compatibility tests from earlier split-lane checkpoints were aligned with the completed v161 state: `listing_crud_uploads` is extracted, `remaining_candidates` is empty, and `recommended_next_lane` is `None`.
