# v152 Listing Promotion View Extraction

LISTING_PROMOTION_VIEW_EXTRACTION_V152

## Purpose

Move the first split-ready listing promotion lane out of `backend/listings/views.py` while preserving public behavior.

## Moved view

- View: `listing_feature_priority_update`
- Old module: `backend/listings/views.py`
- New module: `backend/listings/listing_promotion_views.py`
- Original decorator-inclusive line range before move: 431-452
- Original decorator-inclusive line count before move: 22

## Compatibility guarantee

- `listings.views.listing_feature_priority_update` remains available as a re-export.
- The existing URL callback continues to resolve to the same callable object.
- v151 contract tests continue to lock the POST-only endpoint behavior.
- Decorators are preserved in the extracted module.
- No URL names, routes, templates, models, migrations, permissions, redirects, or business behavior are intentionally changed.

## Verification

- v152 extraction tests confirm the function is no longer defined in `views.py`.
- v152 extraction tests confirm the function is defined in `listing_promotion_views.py`.
- v152 extraction tests confirm `listings.views` re-exports the same function object.
- v152 extraction tests confirm `@login_required` and `@require_POST` are preserved.
- v151 contract tests confirm anonymous GET, authenticated GET, owner POST, and non-owner POST behavior remains stable.

## Next safe step

After v152 is committed and cleanly verified, the next small refactor can target another split-ready lane or add more contract tests for a larger lane before moving it.
