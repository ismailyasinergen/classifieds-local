# v177 Direct Import Migration

LISTING_VIEWS_DIRECT_IMPORT_MIGRATION_V177

## Summary

- Migrated source module: `listing_promotion_views`
- Migrated names: `('listing_feature_priority_update',)`
- Migrated file: `listings/urls.py`
- Original usage form: `direct_from_listings_views_import`
- Dedicated import: `from listings.listing_promotion_views import listing_feature_priority_update`
- Views path: `listings/views.py`
- Views total lines: `155`
- Remaining target migration records: `0`
- Names without migration records after v177: `('listing_feature_priority_update',)`
- v175 candidate names after v177: `('listing_feature_priority_update',)`
- Target group migrated: `True`
- Safe to remove facade re-export in v177: `False`

## Guardrails

- v177 migrates one small dependency group only.
- v177 does not edit `backend/listings/views.py`.
- v177 does not remove any facade re-export.
- A later checkpoint may contract and remove the migrated facade name only after this migration remains green.
