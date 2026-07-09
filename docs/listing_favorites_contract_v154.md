# v154 Favorites Contract Tests

LISTING_FAVORITES_CONTRACT_V154

## Purpose

v154 added focused behavior contracts for the `favorites` lane before moving `listing_favorite_toggle` out of `backend/listings/views.py`.

v155 keeps these contracts green after extracting the view into `backend/listings/listing_favorite_views.py`.

## Locked target

- Lane: `favorites`
- View: `listing_favorite_toggle`
- Dedicated module after v155: `listings.listing_favorite_views`
- Compatibility module: `listings.views`
- URL name: `listing_favorite_toggle`

## Contracts covered

The v154 focused tests lock these behaviors:

- The favorite view remains available through `listings.views` after v155.
- The favorite URL name and callback remain stable.
- Anonymous POST redirects to the resolved login URL with a next parameter.
- Authenticated GET is rejected as method-not-allowed.
- Authenticated POST creates a favorite for the current user.
- A second authenticated POST removes the current user's existing favorite.
- Toggling a favorite is scoped to the current user and does not remove another user's favorite.

## Non-goals

- Do not change URL names or routes.
- Do not change templates.
- Do not change models or migrations.
- Do not change favorite business behavior.

## v155 follow-up

`listing_favorite_toggle` has been extracted into `backend/listings/listing_favorite_views.py` while keeping `listings.views.listing_favorite_toggle` as a re-export.
