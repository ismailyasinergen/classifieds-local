# v157 Browse/Search/Detail View Extraction

BROWSE_SEARCH_DETAIL_VIEW_EXTRACTION_V157

## Purpose

v157 extracts `ListingDetailView` from `backend/listings/views.py` into a dedicated browse/detail view module.

## Extraction

- Lane: `browse_search_detail`
- Extracted class: `ListingDetailView`
- New module: `backend/listings/listing_browse_detail_views.py`
- Supporting dependency copied into the dedicated module: `SidebarCategoriesMixin`
- Compatibility re-export: `listings.views.ListingDetailView`
- URL name kept stable: `listing_detail`
- Runtime URL pattern remains: `/listings/<pk>/`

## Contracts preserved

The v156 browse/search/detail contracts stay green after the move:

- The public URL resolves to `ListingDetailView`.
- Class-based callback resolution still uses `view_class`.
- Public GET remains available.
- Public GET with a search query remains safe.
- `listings.views.ListingDetailView` remains available as the compatibility import path.

## Audit update

The v153 follow-up audit now records three extracted lanes:

- `listing_promotions`
- `favorites`
- `browse_search_detail`

After v157, the next safest remaining split lane is expected to be `uncategorized`.

## Non-goals

- Do not change listing detail behavior.
- Do not change URL names or routes.
- Do not change templates.
- Do not change models or migrations.
- Do not remove the `listings.views` compatibility re-export.
