# v162 Remaining Listing Views Post-v161 Audit

REMAINING_LISTING_VIEWS_POST_V161_AUDIT

## Purpose

After v161 extracted the listing CRUD/upload lane, `backend/listings/views.py` still contains remaining listing-related lanes. This checkpoint records the current remaining shape before another extraction is attempted.

## Current findings

- `views.py` still has 39 top-level definitions/classes.
- `views.py` still has approximately 1,934 lines.
- The largest remaining lane is `listing_reports`.
- The next large remaining lane is `saved_searches`.

## Recommendation

Use v162 as a no-runtime-change audit checkpoint. The next safe implementation checkpoint should protect the `listing_reports` lane with source/runtime contracts before moving it into a dedicated module.

## Non-goals

- Do not move runtime code in v162.
- Do not change URLs, permissions, templates, models, migrations, or runtime behavior.
- Do not remove compatibility re-export paths.
