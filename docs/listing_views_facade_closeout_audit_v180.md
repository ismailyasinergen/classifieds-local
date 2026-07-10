# v180 Listing Views Facade Closeout Audit

LISTING_VIEWS_FACADE_CLOSEOUT_AUDIT_V180

## Summary

- Views path: `backend/listings/views.py`
- URLs path: `backend/listings/urls.py`
- Source path: `backend/listings/listing_promotion_views.py`
- Views total lines: `154`
- Removed target name: `listing_feature_priority_update`
- Target absent from views source: `True`
- Facade re-export import absent: `True`
- Source module still defines target: `True`
- URLs use dedicated import: `True`
- URLs avoid facade import for target: `True`
- Views line count within closeout limit: `True`
- Remaining known candidate names: `()`
- Closeout complete: `True`

## Guardrails

- v180 is an audit-only checkpoint.
- v180 does not change production view, URL, model, template, or migration behavior.
- v180 confirms the v179 facade re-export removal remains stable.
- v180 keeps `backend/docs/` out of the repository.
