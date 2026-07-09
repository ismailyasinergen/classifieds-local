# v153 Split-Lane Follow-Up Audit

LISTING_VIEWS_SPLIT_LANE_FOLLOWUP_AUDIT_V153

## Purpose

This audit records extracted split lanes and selects the next safest split lane from the remaining active lanes.

## Extracted lanes

- `listing_promotions`
  - Extracted view: `listing_feature_priority_update`
  - Extracted module: `backend/listings/listing_promotion_views.py`
  - Checkpoint: v152

- `favorites`
  - Extracted view: `listing_favorite_toggle`
  - Extracted module: `backend/listings/listing_favorite_views.py`
  - Checkpoint: v155

- `browse_search_detail`
  - Extracted view/class: `ListingDetailView`
  - Extracted module: `backend/listings/listing_browse_detail_views.py`
  - Checkpoint: v157

## Recommended next lane after v157

The next safest remaining lane should be `uncategorized`.

Reason: after `listing_promotions`, `favorites`, and `browse_search_detail` are removed from `views.py`, `uncategorized` is the next smallest remaining candidate.

## Verification

The follow-up tests verify that:

- `listing_promotions` is recognized as extracted.
- `favorites` is recognized as extracted.
- `browse_search_detail` is recognized as extracted after v157.
- Extracted lanes are excluded from remaining split candidates.
- Remaining candidates are ordered by smallest definition count, then smallest line count.
- `uncategorized` is selected as the next safest lane after v157.
- Docker test runs do not create `backend/docs/` side effects.

## Non-goals

- Do not move the next lane in this audit checkpoint.
- Do not change URL routes.
- Do not change templates.
- Do not change permissions.
- Do not change models or migrations.
- Do not remove compatibility re-export paths.

## Next safe step

A future checkpoint should add focused contract tests for the `uncategorized` lane before moving it.

## v158 contract checkpoint

UNCATEGORIZED_LANE_CONTRACT_V158

v158 adds focused tests for the `uncategorized` lane before extraction.

Locked v158 audit state:

- Recommended next lane: `uncategorized`
- Remaining candidates: `uncategorized, listing_crud_uploads`
- `uncategorized` definition count: `7`
- `uncategorized` total lines: `100`

v159 can move the `uncategorized` lane after these contracts are green.
