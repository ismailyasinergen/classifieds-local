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

## Recommended next lane after v155

The next safest remaining lane should be `browse_search_detail`.

Reason: after `listing_promotions` and `favorites` are removed from `views.py`, `browse_search_detail` is the smallest remaining single-definition candidate.

## Verification

The v153 follow-up tests verify that:

- `listing_promotions` is recognized as extracted.
- `favorites` is recognized as extracted after v155.
- Extracted lanes are excluded from remaining split candidates.
- Remaining candidates are ordered by smallest definition count, then smallest line count.
- `browse_search_detail` is selected as the next safest lane after v155.
- Docker test runs do not create `backend/docs/` side effects.

## Non-goals

- Do not move the next lane in this audit checkpoint.
- Do not change URL routes.
- Do not change templates.
- Do not change permissions.
- Do not change models or migrations.
- Do not remove compatibility re-export paths.

## Next safe step

A future checkpoint should add focused contract tests for the `browse_search_detail` lane before moving it.

## v156 follow-up

`browse_search_detail` is now protected by focused contract tests before extraction.

- Contract test file: `backend/listings/test_browse_search_detail_contract_v156.py`
- Documentation: `docs/browse_search_detail_contract_v156.md`
- Locked lane: `browse_search_detail`
- Next safe extraction checkpoint: v157
