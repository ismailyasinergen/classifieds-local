# v153 Split-Lane Follow-Up Audit

LISTING_VIEWS_SPLIT_LANE_FOLLOWUP_AUDIT_V153

## Purpose

This audit records extracted split lanes and selects the next safest split lane from the remaining active lanes.

## Extracted lanes after v161

- `listing_promotions`
  - Extracted module: `backend/listings/listing_promotion_views.py`
  - Checkpoint: v152

- `favorites`
  - Extracted module: `backend/listings/listing_favorite_views.py`
  - Checkpoint: v155

- `browse_search_detail`
  - Extracted module: `backend/listings/listing_browse_detail_views.py`
  - Checkpoint: v157

- `uncategorized`
  - Extracted module: `backend/listings/listing_uncategorized_views.py`
  - Checkpoint: v159

- `listing_crud_uploads`
  - Extracted module: `backend/listings/listing_crud_uploads_views.py`
  - Checkpoint: v161

## Completed tracked split-lane state

After v161, all tracked lanes from this split-lane sequence are extracted.

- Remaining candidates: none
- Recommended next split lane: none

## v160 contract checkpoint

LISTING_CRUD_UPLOADS_CONTRACT_V160

v160 locked the `listing_crud_uploads` occurrence-based pre-extraction shape:

- Definition occurrences: `7`
- Audit body-line footprint: `145`
- Decorator-inclusive source span: `149`

## v161 extraction checkpoint

LISTING_CRUD_UPLOADS_VIEW_EXTRACTION_V161

v161 moves those occurrences into `backend/listings/listing_crud_uploads_views.py` and preserves `listings.views` compatibility re-exports.

## Non-goals

- Do not change URL routes.
- Do not change templates.
- Do not change permissions.
- Do not change models or migrations.
- Do not remove compatibility re-export paths.

### v161 Repair 1 import-order follow-up

The completed split-lane state depends on importing `listing_crud_uploads_views` exports before existing `views.py` aliases that reference `ListingCreateView` and related names.

### v161 Repair 2 internal alias follow-up

The completed split-lane state for `listing_crud_uploads` includes internal report-original aliases in `listing_crud_uploads_views.py` to preserve duplicate/shadowed create-update inheritance.

### v161 Repair 3 completed split-lane follow-up

When all tracked split lanes are extracted, the follow-up audit now returns an empty remaining candidate list and records the recommended next lane as `none` instead of raising an error.

### v161 Repair 4 completed split-lane follow-up finalization

The completed-state guard was removed from `build_followup_report()`. When no candidate lanes remain, the report now returns `remaining_candidates = ()` and `recommended_next_lane = None`.


### v161 Repair 6 completed-state compatibility alignment

The completed follow-up report preserves the historical list shape for `remaining_candidates`. Older compatibility tests now recognize that `listing_crud_uploads` is extracted in v161 and therefore no recommended next lane remains.
