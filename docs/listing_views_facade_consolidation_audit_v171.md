# v171 Listing Views Facade Consolidation Audit

LISTING_VIEWS_FACADE_CONSOLIDATION_AUDIT_V171

## Summary

- Views path: `listings/views.py`
- Views total lines: `157`
- Facade-only state: `True`
- Only approved compatibility re-exports remain: `True`
- Wildcard imports present: `False`
- Missing `*_views` re-export modules: `()`
- Missing helper re-export names: `()`

## Protected `*_views` compatibility modules

- `listing_browse_detail_views`
- `listing_crud_uploads_views`
- `listing_favorite_views`
- `listing_promotion_views`
- `listing_reports_views`
- `listing_uncategorized_views`
- `saved_searches_views`

## Protected helper compatibility re-export names

- `_create_moderation_notice`
- `active_approved_listings`
- `apply_listing_filters`
- `default_listing_expiry`
- `save_uploaded_listing_images`
- `validate_uploaded_images`

## Consolidation recommendation

Do not remove helper compatibility re-exports or `*_views` re-export paths yet.

A future checkpoint must first prove that no tests, URL configuration, templates, or external compatibility paths still import these names from `listings.views`.

## Non-goals

- Do not move runtime code in v171.
- Do not remove helper compatibility re-exports in v171.
- Do not remove `*_views` compatibility re-export paths in v171.
- Do not change URLs, templates, permissions, models, migrations, or behavior.
