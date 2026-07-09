# v170 Remove Proven Non-Compatibility Facade Imports

LISTING_VIEWS_IMPORT_CLEANUP_V170

## Purpose

v170 implements the v169 import cleanup contract by removing only proven non-compatibility facade imports from `backend/listings/views.py`.

It preserves every compatibility `*_views` re-export module and the legacy helper compatibility re-exports required by earlier extraction contracts.

## Preserved compatibility `*_views` modules

- `listing_browse_detail_views`
- `listing_crud_uploads_views`
- `listing_favorite_views`
- `listing_promotion_views`
- `listing_reports_views`
- `listing_uncategorized_views`
- `saved_searches_views`

## Preserved helper compatibility re-export names

- `_create_moderation_notice`
- `active_approved_listings`
- `apply_listing_filters`
- `default_listing_expiry`
- `save_uploaded_listing_images`
- `validate_uploaded_images`

## Result

- `backend/listings/views.py` remains facade-only.
- Unexpected non-compatibility imports remaining in `backend/listings/views.py`: `0`
- Wildcard imports remaining in `backend/listings/views.py`: `0`
- Runtime code moved: `False`

## Guardrails

- No URLs were intentionally changed.
- No templates were intentionally changed.
- No permissions were intentionally changed.
- No models or migrations were changed.
- Public URL callbacks that resolve through `listings.views` must still resolve to objects defined outside `listings.views`.
- Legacy helper compatibility re-exports remain available through `listings.views`.

## v174 follow-up

v174 removed only `SidebarCategoriesMixin` and `_safe_reporter_note` from the `listings.views` compatibility facade after the v173 targeted removal contract proved zero facade dependency records for those two names.

All other compatibility `*_views` re-exports and helper compatibility re-exports remain protected.
