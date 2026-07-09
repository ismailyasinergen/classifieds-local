# v167 Post-Extraction Listing Views Audit

POST_EXTRACTION_LISTING_VIEWS_AUDIT_V167

## Summary

- Views path: `listings/views.py`
- Views total lines: `187`
- Top-level functions/classes remaining in `views.py`: `0`
- Has no local runtime views: `True`

## Extracted modules

- `listing_crud_uploads` -> `listings/listing_crud_uploads_views.py` (exists: `True`, re-export mentioned in views: `True`)
- `listing_reports` -> `listings/listing_reports_views.py` (exists: `True`, re-export mentioned in views: `True`)
- `saved_searches` -> `listings/saved_searches_views.py` (exists: `True`, re-export mentioned in views: `True`)

## Remaining local definitions

No top-level functions remain in `listings/views.py`.

No top-level classes remain in `listings/views.py`.

## Compatibility re-export modules detected

- `forms`
- `listing_browse_detail_views`
- `listing_crud_uploads_views`
- `listing_favorite_views`
- `listing_filter_helpers`
- `listing_image_helpers`
- `listing_lifecycle_helpers`
- `listing_moderation_helpers`
- `listing_promotion_views`
- `listing_reports_views`
- `listing_uncategorized_views`
- `listing_visibility_helpers`
- `models`
- `saved_searches_views`

## Recommendation

No further blind extraction from listings/views.py. Use a fresh targeted audit or a compatibility/import hygiene contract before changing runtime code.

## Non-goals

- Do not move runtime code in v167.
- Do not change URLs, templates, permissions, models, migrations, or behavior.
- Do not remove compatibility re-export paths.
- Do not start another extraction without a new contract checkpoint.
