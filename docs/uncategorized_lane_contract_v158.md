# v158 Uncategorized Lane Contract Tests

UNCATEGORIZED_LANE_CONTRACT_V158

## Purpose

v158 adds focused contract tests for the `uncategorized` split lane before moving it out of `backend/listings/views.py`.

This checkpoint is intentionally test/docs only.

## Current audit state after v157

- Current checkpoint before v158: `project-checkpoint-v157-listing-detail-view-extraction`
- Extracted lanes:
  - `listing_promotions`
  - `favorites`
  - `browse_search_detail`
- Recommended next lane: `uncategorized`
- Remaining candidates: `uncategorized, listing_crud_uploads`
- Locked `uncategorized` definition count: `7`
- Locked `uncategorized` total lines: `100`
- Locked readiness: `candidate_for_first_split`

## Contracts added

The v158 tests verify that:

- `uncategorized` is the current recommended next lane.
- Its source footprint is locked before extraction.
- The remaining candidate list is stable after v157.
- Previous extracted lanes remain extracted.
- `uncategorized` has not been moved into a dedicated module yet.
- Generated follow-up markdown documents `uncategorized` as the next split lane.

## Non-goals

- Do not move the `uncategorized` lane in v158.
- Do not change routes.
- Do not change templates.
- Do not change permissions.
- Do not change models or migrations.
- Do not change runtime behavior.

## Next safe step

v159 can extract the `uncategorized` lane into a dedicated module while preserving any required `listings.views` compatibility re-exports.

## v159 follow-up

The `uncategorized` lane has been extracted into `backend/listings/listing_uncategorized_views.py`.

The v158 contracts now validate the same v158 audit footprint (`100` lines) through the dedicated module and the `listings.views` compatibility re-exports. The extracted source preserves decorators, giving a decorator-inclusive source span of `104` lines. The AST body-line footprint is `94` lines.

Repair 4 also removes shadowed duplicate top-level target definitions from `views.py` so compatibility re-exports cannot be shadowed.

After this extraction, the next safest lane is `listing_crud_uploads`.

### Repair 5 import-order follow-up

The v159 compatibility re-export block is placed before early `views.py` classes that still inherit from `SidebarCategoriesMixin`.

### Repair 8 byte-safe assignment-alias dependency follow-up

`_BaseAttributeListingListView` is preserved as an internal assignment alias in `listing_uncategorized_views.py`, together with the earlier `ListingListView` base it points to. The source recovery uses byte-safe UTF-8 decoding for the original v158 file.
