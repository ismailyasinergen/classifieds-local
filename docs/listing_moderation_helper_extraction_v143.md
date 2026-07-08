# v143 Listing Moderation Notice Helper Extraction

v143 extracts `_create_moderation_notice` from `backend/listings/views.py` into:

`backend/listings/listing_moderation_helpers.py`

## Why this was next

v141 locked `_create_moderation_notice` as a low-risk first-extraction candidate:

- private helper
- short function
- non-view helper
- behavior can be protected by listing report, trust/safety, and smoke tests

## Behavior contract

The extraction must keep these unchanged:

- listing report moderation flow
- listing suspension flow
- moderation notice creation behavior
- trust/safety event behavior
- user-visible redirects and messages
- existing URLs, templates, models, and migrations

## Import hygiene

`listing_moderation_helpers.py` should not copy broad view-only imports from `views.py`.
It should only import names required by `_create_moderation_notice`.

## v143 non-goals

- Do not change URLs.
- Do not change templates.
- Do not change models or migrations.
- Do not change report or suspension behavior.
- Do not extract additional helpers yet.

## v141 audit compatibility

v142 extracted `apply_listing_filters` and v143 extracts `_create_moderation_notice`.
Those were the two low-risk candidates locked by v141, so the v141 audit test now allows the active low-risk candidate count to reach zero after successful extraction.
