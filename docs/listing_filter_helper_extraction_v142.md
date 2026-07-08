# v142 Listing Filter Helper Extraction

v142 extracts `apply_listing_filters` from `backend/listings/views.py` into:

`backend/listings/listing_filter_helpers.py`

## Why this was first

v141 locked `apply_listing_filters` as a low-risk first extraction candidate:

- non-view helper
- query/filter oriented
- under 120 lines
- behavior can be protected by existing filter tests

## Behavior contract

The extraction must keep these unchanged:

- listing browse filters
- category attribute filters
- numeric range filters
- price/search/category filter combinations
- pagination query strings
- active filter chips and clear links

## v142 non-goals

- Do not change URLs.
- Do not change templates.
- Do not change models or migrations.
- Do not change filter behavior.
- Do not extract `_create_moderation_notice` yet.

## Import hygiene

`listing_filter_helpers.py` should not copy broad view-only imports from `views.py`.
It should only import names required by `apply_listing_filters`.
