# v174 Remove Two Unused Listing Views Facade Re-exports

LISTING_VIEWS_TARGETED_REEXPORT_REMOVAL_V174

## Summary

- Views path: `listings/views.py`
- Views total lines: `155`
- Removed exactly target pair: `True`
- Target names present in facade: `()`
- Target names absent from facade: `('SidebarCategoriesMixin', '_safe_reporter_note')`
- Missing expected remaining names: `()`
- Unexpected remaining names: `()`
- Facade-only state preserved: `True`
- Import hygiene preserved: `True`
- Helper compatibility re-exports preserved: `True`
- Target facade dependency count: `0`

## Removed from `listings.views` only

- `SidebarCategoriesMixin`
- `_safe_reporter_note`

## Preserved source modules

- `SidebarCategoriesMixin` remains defined/exported by `listing_uncategorized_views`
- `_safe_reporter_note` remains defined/exported by `listing_reports_views`

## Guardrails

- No runtime implementation code was moved.
- No URLs, templates, permissions, models, migrations, or behavior were intentionally changed.
- Every non-target compatibility re-export remains protected.
- Route callback identity through the remaining facade exports remains protected.
