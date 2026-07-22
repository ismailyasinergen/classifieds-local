# v321 — Mobile listing buyer action bar

MOBILE_LISTING_BUYER_ACTION_BAR_V321=1

## Purpose

V321 gives mobile buyers persistent access to the three highest-value listing
actions without changing the desktop information architecture or introducing a
new API: message the seller, save or remove the listing, and share the listing.

## Buyer-action contract

The action bar renders only for approved listings and only when the visitor is
neither the listing owner nor staff.

- anonymous visitors receive login links whose `next` values return to the
  message composer or listing detail as appropriate;
- authenticated buyers use the existing message URL and the existing
  CSRF-protected favorite POST endpoint;
- save/remove state comes from the established favorite context;
- both desktop and mobile share buttons use the v317 Web Share and clipboard
  fallback implementation;
- the bar is hidden outside the mobile breakpoint and in print output;
- safe-area padding, page-bottom clearance, and 44-pixel minimum targets avoid
  overlap with content and device UI.

## Audit repairs included in the checkpoint

The pre-v321 repository audit found no Critical issue. The checkpoint closes
the following High and safely bounded Medium findings:

- expired approved listings can no longer be favorited or used to open a new
  message composer; both paths use the shared active-approved visibility rule;
- three staff listing feature endpoints and the moderation-notice read endpoint
  now reject cross-origin `next` redirects and fall back to local destinations;
- conversation inbox unread counts are aggregated in one query instead of one
  query per listing/sender thread.

Large shadowed-view modules, remaining staff-only CSV formula-neutralization
review, and listing-detail asset extraction are recorded in `ROADMAP_STATUS.md`
as separately scoped follow-up work.

## Validation evidence

- 5 focused v321 tests passed;
- 45 combined v317-v321 and audit-repair tests passed;
- 98 v150-v162 extraction, footprint, and redirect compatibility tests passed;
- the complete PostgreSQL suite passed with 2,854 tests in 419.758 seconds;
- Django system and template checks passed;
- `makemigrations --check --dry-run` reported no changes;
- a 390×844 browser render confirmed 76-pixel page clearance, three 46.4-pixel
  action targets, fixed-bottom placement, no horizontal overflow, and no
  page-end content overlap;
- `git diff --check` reported no whitespace errors before staging.

The expected warnings in the complete suite exercise deliberate 4xx, provider
failure, and permission-denied paths; the run ended with an explicit `OK`.

## Repository and migration scope

V321 changes existing views and templates, adds regression tests and updates
documentation. It adds no model, migration, package, service, secret, generated
artifact, or development-database mutation.

Checkpoint tag:

    project-checkpoint-v321-mobile-listing-buyer-action-bar

The annotated tag resolves the exact checkpoint commit.

## Next milestone

V322 performs the listing-detail accessibility audit and applies only verified,
bounded fixes with regression coverage.
