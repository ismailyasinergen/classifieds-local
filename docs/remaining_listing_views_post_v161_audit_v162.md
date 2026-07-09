# v162 Remaining Listing Views Post-v161 Audit

REMAINING_LISTING_VIEWS_POST_V161_AUDIT

## Purpose

After v161 extracted the listing CRUD/upload lane, this audit recorded the remaining listing-related lanes in `backend/listings/views.py`.

## Original v162 findings

At the v162 checkpoint:

- `listing_reports` was the largest remaining lane.
- `saved_searches` was the next large remaining lane.
- `listing_reports` was recommended as the next extraction target.

## v164 follow-up

v164 extracted the protected `listing_reports` lane into `backend/listings/listing_reports_views.py`.

After v164, the remaining lane in `backend/listings/views.py` is:

- `saved_searches`

## Next safe step after v164

Prepare a contract checkpoint for the `saved_searches` lane before moving any saved-search runtime code.

## Non-goals

- Do not change URLs, permissions, templates, models, migrations, or runtime behavior as part of this audit.
- Do not remove compatibility re-export paths.
