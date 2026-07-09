# v159 Uncategorized Lane View Extraction

UNCATEGORIZED_LANE_VIEW_EXTRACTION_V159

## Purpose

v159 extracts the `uncategorized` lane from `backend/listings/views.py` into a dedicated module while preserving `listings.views` compatibility re-exports.

## Extraction

- Lane: `uncategorized`
- New module: `backend/listings/listing_uncategorized_views.py`
- Compatibility re-export path: `listings.views`
- Extracted definition count: `7`
- V158 audit footprint: `100`
- AST body-line footprint: `94`
- Decorator-inclusive extracted source span: `104`
- Duplicate/shadowed target definitions removed from `views.py`: `{"ListingListView": [{"start": 66, "body_start": 66, "end": 84}, {"start": 1595, "body_start": 1595, "end": 1617}]}`
- Extracted names:
  - `SidebarCategoriesMixin`
  - `ListingListView`
  - `listing_approve`
  - `listing_reject`
  - `listing_archive`
  - `listing_renew`
  - `listing_feature_toggle`

## Audit update

After v159, extracted lanes are:

- `listing_promotions`
- `favorites`
- `browse_search_detail`
- `uncategorized`

The next safest remaining split lane is now `listing_crud_uploads`.

## Non-goals

- Do not change routes.
- Do not change templates.
- Do not change permissions.
- Do not change models or migrations.
- Do not change runtime behavior beyond moving active source definitions and removing shadowed duplicate definitions with the same top-level names.

## Next safe step

v160 can add focused contract tests for the `listing_crud_uploads` lane before moving it.

## Repair 5 import-order follow-up

The `listings.views` compatibility re-export for `SidebarCategoriesMixin` and the other `uncategorized` exports must appear before early view classes such as `ListingCreateView` consume `SidebarCategoriesMixin`.

Repair 5 moves the re-export block near the top of `views.py` and adds a regression test for this import order.

## Repair 8 byte-safe assignment-alias dependency follow-up

`_BaseAttributeListingListView` is a top-level assignment alias, not a class definition.

Repair 8 reads the original v158 source through byte-safe UTF-8 decoding, then moves that alias and its earlier `ListingListView` base dependency into `listing_uncategorized_views.py` before the active exported `ListingListView`. The active export remains the last `ListingListView` definition in the dedicated module.
