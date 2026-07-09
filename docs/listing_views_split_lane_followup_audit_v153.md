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

- `uncategorized`
  - Extracted definitions: `SidebarCategoriesMixin, ListingListView, listing_approve, listing_reject, listing_archive, listing_renew, listing_feature_toggle`
  - Extracted module: `backend/listings/listing_uncategorized_views.py`
  - Checkpoint: v159
  - V158 audit footprint: `100`
  - AST body-line footprint: `94`
  - Decorator-inclusive source span: `104`
  - Shadowed duplicate target definitions removed from `views.py`: `{"ListingListView": [{"start": 66, "body_start": 66, "end": 84}, {"start": 1595, "body_start": 1595, "end": 1617}]}`

## Recommended next lane after v159

The next safest remaining lane should be `listing_crud_uploads`.

Reason: after `listing_promotions`, `favorites`, `browse_search_detail`, and `uncategorized` are removed from `views.py`, `listing_crud_uploads` is the remaining candidate.

## Verification

The follow-up tests verify that:

- `listing_promotions` is recognized as extracted.
- `favorites` is recognized as extracted.
- `browse_search_detail` is recognized as extracted.
- `uncategorized` is recognized as extracted after v159.
- Extracted lanes are excluded from remaining split candidates.
- `listing_crud_uploads` is selected as the next safest lane after v159.
- Docker test runs do not create `backend/docs/` side effects.

## Non-goals

- Do not move the next lane in this audit checkpoint.
- Do not change URL routes.
- Do not change templates.
- Do not change permissions.
- Do not change models or migrations.
- Do not remove compatibility re-export paths.

## v158 contract checkpoint

UNCATEGORIZED_LANE_CONTRACT_V158

v158 added focused tests for the `uncategorized` lane before extraction.

Locked v158 audit state:

- Recommended next lane before v159: `uncategorized`
- Remaining candidates before v159: `uncategorized, listing_crud_uploads`
- `uncategorized` definition count: `7`
- `uncategorized` audit footprint: `100`
- `uncategorized` AST body-line footprint: `94`
- `uncategorized` decorator-inclusive extraction span: `104`

## v159 extraction checkpoint

UNCATEGORIZED_LANE_VIEW_EXTRACTION_V159

v159 moves the `uncategorized` lane into `backend/listings/listing_uncategorized_views.py`.

## Next safe step

A future checkpoint should add focused contract tests for the `listing_crud_uploads` lane before moving it.

### Repair 5 import-order follow-up

The v159 `uncategorized` extraction keeps `listings.views` compatibility by importing the dedicated module exports before any remaining local view classes consume `SidebarCategoriesMixin`.

### Repair 8 byte-safe assignment-alias dependency follow-up

The v159 extraction preserves the `_BaseAttributeListingListView` assignment alias and its internal base dependency inside `listing_uncategorized_views.py`. Repair 8 uses byte-safe decoding when reading the original v158 source.

## v160 listing_crud_uploads contract checkpoint

LISTING_CRUD_UPLOADS_CONTRACT_V160

v160 adds focused pre-extraction contracts for the final remaining lane: `listing_crud_uploads`.

Locked v160 state:

- Recommended next lane: `listing_crud_uploads`
- Remaining candidates: `listing_crud_uploads`
- Definition occurrences: `7`
- Audit total lines: `145`
- Decorator-inclusive source span: `149`

Locked definition occurrences:

- `ListingCreateView` (class), lines 52-84, line count 33
- `ListingUpdateView` (class), lines 87-126, line count 40
- `ListingDeleteView` (class), lines 129-143, line count 15
- `listing_image_delete` (function), lines 148-161, line count 14
- `listing_feature_days_update` (function), lines 241-261, line count 21
- `ListingCreateView` (class), lines 1152-1162, line count 11
- `ListingUpdateView` (class), lines 1166-1176, line count 11

Next safe step: v161 can extract `listing_crud_uploads` into a dedicated module.

### v160 Repair 2 Docker test-path follow-up

The v160 contract test avoids direct reads of repo-root docs during Docker test execution. Host-side script checks still validate `docs/listing_crud_uploads_contract_v160.md`.
