# v145 Listing Lifecycle Helper Extraction

v145 extracts `default_listing_expiry` from `backend/listings/views.py` into:

`backend/listings/listing_lifecycle_helpers.py`

## Why this was next

v144 refreshed the remaining `backend/listings/views.py` extraction audit and identified `default_listing_expiry` as the safest next candidate:

- 2 lines
- low risk
- non-view helper
- no request-first signature
- no template/render/redirect behavior

## Behavior contract

The extraction must keep these unchanged:

- listing creation defaults
- listing expiry behavior
- public listing visibility behavior
- existing URLs, templates, models, and migrations

## Import hygiene

`listing_lifecycle_helpers.py` should only import names required by lifecycle helpers.
It must not copy view-only imports such as mixins, render/redirect helpers, pagination, or messages.

## v145 non-goals

- Do not change listing expiry duration.
- Do not change listing status behavior.
- Do not change listing visibility behavior.
- Do not change models or migrations.
- Do not extract additional lifecycle helpers yet.
