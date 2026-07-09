# v155 Favorite View Extraction

LISTING_FAVORITE_VIEW_EXTRACTION_V155

## Purpose

v155 extracts `listing_favorite_toggle` from `backend/listings/views.py` into a dedicated favorite view module.

## Extraction

- Moved view: `listing_favorite_toggle`
- New module: `backend/listings/listing_favorite_views.py`
- Compatibility re-export: `listings.views.listing_favorite_toggle`
- URL name kept stable: `listing_favorite_toggle`

## Contracts preserved

The v154 favorites contracts stay green after the move:

- URL name and callback are stable.
- Anonymous POST redirects to the resolved login URL with `next`.
- Authenticated GET returns 405.
- Authenticated POST creates a favorite for the current user.
- A second authenticated POST removes the current user's favorite.
- The favorite toggle remains scoped to the current user.

## Audit update

The split-lane follow-up audit now records both extracted lanes:

- `listing_promotions` extracted in v152
- `favorites` extracted in v155

After v155, the next safest remaining split lane is expected to be `browse_search_detail`.

## Non-goals

- Do not change favorite behavior.
- Do not change URL names or routes.
- Do not change templates.
- Do not change models or migrations.
- Do not remove the `listings.views` compatibility re-export.
