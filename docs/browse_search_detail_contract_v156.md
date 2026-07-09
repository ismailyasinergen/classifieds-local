# v156 Browse/Search/Detail Contract Tests

BROWSE_SEARCH_DETAIL_CONTRACT_V156

## Purpose

v156 adds focused contract tests for the `browse_search_detail` lane before moving its remaining view out of `backend/listings/views.py`.

This checkpoint is test/docs only. It does not move the view.

## Locked target

- Lane: `browse_search_detail`
- Current module: `listings.views`
- Target definition: `ListingDetailView`
- Current state: one remaining definition
- Next expected extraction checkpoint: v157

## Contracts covered

The v156 tests lock these behaviors:

- The v153 follow-up audit still recommends `browse_search_detail` as the next safest lane.
- The lane still has exactly one remaining definition before extraction.
- The target view is still defined in `listings.views`.
- The target route resolves to the current `listings.views` callback.
- Public GET access to the route remains available.
- Public GET with a search query remains safe and does not require login.

## Non-goals

- Do not move the target view in v156.
- Do not create a new browse/search/detail view module yet.
- Do not change URL names or routes.
- Do not change templates.
- Do not change permissions.
- Do not change models or migrations.

## Next safe step

v157 can extract the `browse_search_detail` target view into a dedicated module while keeping the `listings.views` compatibility re-export and keeping these v156 contracts green.
