# v154 Favorites Contract Tests

LISTING_FAVORITES_CONTRACT_V154

## Purpose

v154 adds focused behavior contracts for the `favorites` lane before moving `listing_favorite_toggle` out of `backend/listings/views.py`.

This checkpoint is test/docs only. It does not move the view.

## Locked target

- Lane: `favorites`
- View: `listing_favorite_toggle`
- Current public module: `listings.views`
- URL name: `listing_favorite_toggle`

## Contracts covered

The v154 focused tests lock these behaviors:

- The v153 follow-up audit still recommends `favorites` as the next safest lane.
- The favorite URL name and callback remain stable.
- Anonymous POST redirects to the resolved login URL with a next parameter.
- Authenticated GET is rejected as method-not-allowed.
- Authenticated POST creates a favorite for the current user.
- A second authenticated POST removes the current user's existing favorite.
- Toggling a favorite is scoped to the current user and does not remove another user's favorite.

## Non-goals

- Do not move `listing_favorite_toggle` in v154.
- Do not create a new favorites view module yet.
- Do not change URL names or routes.
- Do not change templates.
- Do not change models or migrations.
- Do not change favorite business behavior.

## Next safe step

v155 can move `listing_favorite_toggle` into a dedicated favorites view module while keeping `listings.views.listing_favorite_toggle` as a re-export and keeping these v154 contracts green.
