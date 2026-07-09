# v165 Saved Searches Contract Checkpoint

SAVED_SEARCHES_CONTRACT_V165

## Purpose

This checkpoint protects the `saved_searches` lane before and during extraction from `backend/listings/views.py`.

After v164 extracted `listing_reports`, the v162 remaining-views audit recommended `saved_searches` as the next extraction lane.

## Scope

The contract records and protects:

- the six saved-search callbacks,
- the active source footprint for each callback,
- URL resolver identity for the current saved-search routes,
- current callback identity through `listings.views`,
- existing saved-search runtime test coverage.

## Protected saved-search callbacks

- `saved_search_create`: `28` lines
- `saved_search_list`: `358` lines
- `saved_search_notifications_toggle`: `36` lines
- `saved_search_delete`: `7` lines
- `saved_search_bulk_action`: `49` lines
- `saved_search_rename`: `48` lines

Total saved-search lane footprint: `526` lines.

## Protected route behavior

Saved-search routes are protected through Django's URL resolver.

Each protected callback must have at least one URL route resolving to the current `listings.views.<callback>` object:

- `saved_search_create`
- `saved_search_list`
- `saved_search_notifications_toggle`
- `saved_search_delete`
- `saved_search_bulk_action`
- `saved_search_rename`

## v166 extraction follow-up

v166 extracts the protected saved-search lane into `backend/listings/saved_searches_views.py`.

Compatibility remains available through `listings.views` re-exports, so URL configuration and callers can continue using existing `views.<callback>` references.

## Non-goals

- Do not change URLs, permissions, templates, models, migrations, or runtime behavior.
- Do not remove compatibility access through `listings.views`.

## Next safe step after v166

Run a fresh post-extraction audit before choosing the next cleanup target.
