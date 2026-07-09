# v166 Saved Searches View Extraction

SAVED_SEARCHES_VIEW_EXTRACTION_V166

## Summary

v166 extracts the protected saved-search lane from `backend/listings/views.py` into:

- `backend/listings/saved_searches_views.py`

Compatibility is preserved through `listings.views` re-exports.

## Preserved callbacks

The following callbacks remain accessible through `listings.views`:

- `saved_search_create`
- `saved_search_list`
- `saved_search_notifications_toggle`
- `saved_search_delete`
- `saved_search_bulk_action`
- `saved_search_rename`

## Runtime behavior

No runtime behavior should change in v166.

The extraction preserves:

- saved-search create flow,
- saved-search management/list page,
- notification toggle,
- delete action,
- bulk action,
- rename action,
- route callback identity through `listings.views`,
- existing saved-search runtime test coverage.

## Remaining views audit state

After v166, the v162 remaining-views audit has no remaining candidate lanes.

## Next safe step

Run a fresh post-extraction audit before choosing the next cleanup target.
