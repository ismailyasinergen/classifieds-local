# v179 Listing Feature Priority Facade Re-export Removal

LISTING_FEATURE_PRIORITY_REEXPORT_REMOVAL_V179

## Summary

- Removed facade re-export: `listing_feature_priority_update`
- Source module kept: `listing_promotion_views`
- Dedicated import retained: `from listings.listing_promotion_views import listing_feature_priority_update`
- Views path: `listings/views.py`
- Views total lines: `154`
- Removed from facade source: `True`
- Absent from runtime facade: `True`
- Source module still defines name: `True`
- URLs use dedicated import: `True`
- URLs avoid facade import for target: `True`
- v175 candidate names after v179: `()`
- v176 names without migration records after v179: `()`
- v177 target group migrated: `True`
- v178 contract satisfied by v179: `True`
- Removal complete: `True`

## Guardrails

- v179 removes only `listing_feature_priority_update` from `backend/listings/views.py`.
- v179 keeps `backend/listings/listing_promotion_views.py` intact.
- v179 keeps `backend/listings/urls.py` intact.
- v179 does not remove any other facade re-export.
