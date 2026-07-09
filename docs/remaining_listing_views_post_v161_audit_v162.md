# v162 Remaining Listing Views Post-v161 Audit

REMAINING_LISTING_VIEWS_POST_V161_AUDIT

## Purpose

After v161 extracted the listing CRUD/upload lane, this audit recorded the remaining listing-related lanes in `backend/listings/views.py`.

## Original v162 findings

At the v162 checkpoint:

- `listing_reports` was the largest remaining lane.
- `saved_searches` was the next large remaining lane.
- `listing_reports` was recommended as the next extraction target.

## Follow-up extraction history

- v164 extracted the protected `listing_reports` lane into `backend/listings/listing_reports_views.py`.
- v166 extracted the protected `saved_searches` lane into `backend/listings/saved_searches_views.py`.

After v166, there are no remaining candidate lanes in `backend/listings/views.py` for this audit.

## Next safe step after v166

Run a fresh post-extraction audit to decide whether any smaller cleanup or view split opportunities remain outside the original lane list.

## Non-goals

- Do not change URLs, permissions, templates, models, migrations, or runtime behavior as part of this audit.
- Do not remove compatibility re-export paths.
