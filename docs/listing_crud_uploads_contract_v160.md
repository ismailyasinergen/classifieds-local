# v160 Listing CRUD Uploads Contract

LISTING_CRUD_UPLOADS_CONTRACT_V160

## Purpose

v160 locks the current `listing_crud_uploads` lane before extraction.

This checkpoint is intentionally test/docs only. It should not move code out of `backend/listings/views.py`.

The contract is occurrence-based because this lane currently includes duplicate/shadowed top-level class definitions.

## Current audit state

- Current recommended next split lane: `listing_crud_uploads`
- Remaining candidates: `listing_crud_uploads`
- Definition occurrences: `7`
- Audit total lines: `145`
- Decorator-inclusive source span: `149`

## Definition occurrences locked by v160

- `ListingCreateView` (class), lines 52-84, line count 33
- `ListingUpdateView` (class), lines 87-126, line count 40
- `ListingDeleteView` (class), lines 129-143, line count 15
- `listing_image_delete` (function), lines 148-161, line count 14
- `listing_feature_days_update` (function), lines 241-261, line count 21
- `ListingCreateView` (class), lines 1152-1162, line count 11
- `ListingUpdateView` (class), lines 1166-1176, line count 11

## Unique target names

- `ListingCreateView` x 2
- `ListingUpdateView` x 2
- `ListingDeleteView` x 1
- `listing_image_delete` x 1
- `listing_feature_days_update` x 1

## Route-linked targets discovered

- `ListingCreateView`
- `ListingUpdateView`
- `ListingDeleteView`
- `listing_image_delete`
- `listing_feature_days_update`

## Current extracted lanes that must remain extracted

- `browse_search_detail`
- `favorites`
- `listing_promotions`
- `uncategorized`

## Pre-extraction expectations

- Every locked definition occurrence still exists in `backend/listings/views.py`.
- Every unique locked target name is importable through `listings.views`.
- No dedicated `listing_crud_uploads_views.py` module exists yet.
- `views.py` does not import from `listing_crud_uploads_views`.
- The follow-up audit still recommends `listing_crud_uploads`.
- Previously extracted lanes remain extracted.

## Non-goals

- Do not extract the lane in v160.
- Do not change URL routes.
- Do not change templates.
- Do not change permissions.
- Do not change models or migrations.
- Do not change runtime behavior.

## Next safe step

v161 can extract `listing_crud_uploads` into a dedicated module while preserving required `listings.views` compatibility re-exports and handling duplicate/shadowed class occurrences safely.

## Repair 2 Docker test-path follow-up

The v160 Django test suite does not directly read this repo-root docs file at runtime, because Docker tests run from `/app` and repo-root `docs/` is not available there.

Instead, the focused test validates the locked contract metadata embedded in `test_listing_crud_uploads_contract_v160.py`, while host-side script checks verify this documentation file.
