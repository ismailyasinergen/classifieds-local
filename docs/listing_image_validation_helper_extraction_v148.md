# v148 Listing Image Validation Helper Extraction

v148 extracts `validate_uploaded_images` from `backend/listings/views.py` into the existing image helper module:

`backend/listings/listing_image_helpers.py`

## Why this was next

After v147, the remaining extraction audit identified `validate_uploaded_images` as the only remaining helper candidate:

- 19 lines
- low risk
- non-view helper
- no request-first signature
- listing image validation helper

## Behavior contract

The extraction must keep these unchanged:

- uploaded image validation behavior
- allowed image content-type checks
- image size limits
- image count limits
- listing creation and edit upload flows
- existing URLs, templates, models, and migrations

## Import hygiene

`listing_image_helpers.py` should contain only listing image helper dependencies.

## v148 non-goals

- Do not change upload validation rules.
- Do not change error text.
- Do not change allowed image types.
- Do not change upload limits.
- Do not change models or migrations.
