# v322 — Listing detail accessibility

LISTING_DETAIL_ACCESSIBILITY_V322=1

## Purpose

V322 audits the listing-detail experience for keyboard, screen-reader, motion,
and semantic-structure regressions after the v317-v321 interaction milestones.
It applies bounded template and client-side fixes without changing listing data
or backend authorization.

## Findings and fixes

The audit found no Critical or High security issue. It closed these verified
accessibility defects:

- the category tree preceded the listing in DOM and mobile visual order;
- there was no shared keyboard skip path to primary content;
- the category heading started at level three before the listing heading;
- interactive listing controls did not share a strong focus-visible treatment;
- listing-detail motion did not honor the reduced-motion preference;
- the gallery fallback lacked explicit modal semantics, Escape handling, and a
  contained Tab/Shift+Tab focus loop.

The shared shell now places primary content first in DOM, preserves the desktop
sidebar column through explicit grid placement, and keeps the historical
sidebar-first visual order on other mobile pages. Listing-detail mobile pages
show the listing before categories.

The gallery retains v318 arrow navigation and origin-focus restoration while
adding explicit `aria-modal`, Escape closure, and focus wrapping across its
close/previous/next controls.

## Regression contract

The v322 tests verify:

- one skip link targeting one focusable primary-content node;
- one main landmark, one initial h1, no heading-level jump, and unique rendered
  IDs;
- main-content-first source order and listing-specific mobile ordering;
- modal gallery Tab, Shift+Tab, Escape, and focus-restore source contracts;
- explicit status/live-region semantics;
- focus-visible and reduced-motion CSS;
- absence of a v322 migration.

## Validation evidence

- 7 focused v322 tests passed;
- 129 combined v235, v238-v240, and v317-v322 compatibility tests passed;
- the complete PostgreSQL suite passed with 2,861 tests in 400.256 seconds;
- Django system and template checks passed;
- `makemigrations --check --dry-run` reported no changes;
- `git diff --check` reported no whitespace errors before staging.

The expected complete-suite warnings exercise deliberate 4xx, provider-failure,
and permission-denied paths; the run ended with an explicit `OK`.

## Repository and migration scope

V322 changes the shared base template, category sidebar heading, listing-detail
template, tests, roadmap, and this document. It adds no model, migration,
package, service, secret, generated artifact, or development-database mutation.

Checkpoint tag:

    project-checkpoint-v322-listing-detail-accessibility

The annotated tag resolves the exact checkpoint commit.

## Next milestone

V323 applies a shared spreadsheet-formula neutralization contract to remaining
staff-only CSV exports identified by the repository audit.
