# v325 - Listing-detail extraction blocker removal

LISTING_DETAIL_EXTRACTION_BLOCKER_REMOVAL_V325=1

## Purpose

V325 clears the two blockers identified by the v324 listing-detail asset audit
without physically extracting CSS or JavaScript. It removes inline image error
handlers and moves legacy source-reading tests onto one asset-aware contract.

Rendered listing behavior, asset loading order, URLs, permissions, data models,
and database state are unchanged.

## Image fallback behavior

The main listing image and each thumbnail now declare a stable
`data-listing-image-fallback-v325` hook instead of an inline `onerror`
attribute. The existing gallery script registers one-shot `error` listeners
that create the same placeholder element, class, and `No image` text.

The listener also checks `complete` and `naturalWidth` after registration. This
preserves fallback behavior when an image failed before the bottom-of-page
script attached, while the event listener handles later failures.

## Asset-aware source contract

`read_listing_detail_contract_source_v325` reads the listing-detail template
followed by each existing planned static asset in deterministic order. The
current checkpoint has no extracted assets, so only the template is present.
The contract already recognizes these future paths:

    listings/static/listings/listing-detail-v324.css
    listings/static/listings/listing-detail-v324.js

Eleven legacy test modules were migrated from direct template reads. The live
audit reports twelve asset-aware consumers because the new v325 regression
module also consumes the shared contract.

## Audit state

The v324 audit remains the operator interface and now reports:

- zero inline event handlers;
- zero legacy source-contract tests;
- twelve asset-aware source-contract tests;
- four remaining inline `style=` attributes;
- one template-independent style block and four template-independent script
  blocks;
- `cutover_ready=true` and `strict_csp_ready=false`.

Inline style attributes are included in strict-CSP readiness so that a later
asset extraction cannot overclaim CSP completion. They are not blockers for
moving the large style and script blocks into static files.

## Validation evidence

- 15 combined v324-v325 focused tests passed;
- 146 combined v271-v275, v283, v317-v319, and v321-v325 compatibility tests
  passed;
- the complete PostgreSQL suite passed with 2,883 tests in 384.497 seconds;
- Django system and template checks passed;
- `makemigrations --check --dry-run` reported no changes;
- `git diff --check` reported no whitespace errors before staging.

The expected complete-suite warnings exercise deliberate 4xx,
provider-failure, and permission-denied paths; the run ended with an explicit
`OK`.

## Repository and migration scope

V325 adds one source-contract helper and one regression module, updates the
read-only audit, replaces two template event attributes with equivalent
listener behavior, migrates eleven test consumers, and updates documentation.
It adds no static asset, model, migration, package, service, secret, generated
artifact, or development-database mutation.

Checkpoint tag:

    project-checkpoint-v325-listing-detail-extraction-blockers

The annotated tag resolves the exact checkpoint commit.

## Next milestone

V326 extracts only the listing-detail CSS block into the planned versioned
static file. JavaScript remains inline until the CSS cutover, loading-order
contract, and complete regression baseline are independently proven.
