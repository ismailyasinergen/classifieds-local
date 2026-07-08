# v146 Listing Visibility Helper Extraction

v146 extracts `active_approved_listings` from `backend/listings/views.py` into:

`backend/listings/listing_visibility_helpers.py`

## Why this was next

After v145, the remaining extraction audit identified `active_approved_listings` as the next safest candidate:

- 6 lines
- low risk
- non-view helper
- no request-first signature
- query visibility helper

## Behavior contract

The extraction must keep these unchanged:

- public browse listing visibility
- seller storefront public listing visibility
- active/approved listing filtering
- expired listing exclusion behavior
- existing URLs, templates, models, and migrations

## Import hygiene

`listing_visibility_helpers.py` should only import names required by visibility query helpers.

## v146 non-goals

- Do not change listing visibility rules.
- Do not change listing status rules.
- Do not change seller storefront filtering.
- Do not change models or migrations.
- Do not extract upload helpers yet.
