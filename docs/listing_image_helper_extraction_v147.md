# v147 Listing Image Helper Extraction

v147 extracts `save_uploaded_listing_images` from `backend/listings/views.py` into:

`backend/listings/listing_image_helpers.py`

## Why this was next

After v146, the remaining extraction audit identified `save_uploaded_listing_images` as the next safest candidate:

- 11 lines
- low risk
- non-view helper
- no request-first signature
- listing image persistence helper

## Behavior contract

The extraction must keep these unchanged:

- listing creation image saving
- listing edit image saving
- listing image ordering behavior
- uploaded file persistence
- existing URLs, templates, models, and migrations

## Import hygiene

`listing_image_helpers.py` should only import names required by listing image helpers.

## v147 non-goals

- Do not change upload validation rules.
- Do not change allowed image types.
- Do not change image count limits.
- Do not change models or migrations.
- Do not extract `validate_uploaded_images` yet.
