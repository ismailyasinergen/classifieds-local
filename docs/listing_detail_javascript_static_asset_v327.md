# v327 - Listing-detail JavaScript static asset

LISTING_DETAIL_JAVASCRIPT_STATIC_ASSET_V327=1

## Purpose

V327 moves all four template-independent listing-detail script blocks into the
planned versioned static JavaScript file. The external script remains at the
same bottom-of-page execution point and does not use `defer` or `async`, so DOM
availability and feature order are preserved.

The extraction does not redesign interactions, change selectors, introduce a
bundler, tighten CSP, or mutate application data.

## Static execution contract

The listing-detail template now contains exactly one script include:

    /static/listings/listing-detail-v324.js

It appears after the gallery, lightbox, location, share, and print DOM hooks.
The combined file preserves the original feature order:

1. gallery switching and v325 image fallback listeners;
2. v318 full-screen lightbox;
3. v319 location copy;
4. v317 share, copy-link, print, and status announcements.

A real approved-listing response verifies that the external script is rendered
once and after the interaction DOM.

## Extraction integrity

The four v326 inline bodies contained 18,484 characters including template
indentation. V327 removes only their common indentation, joins them in original
order, and adds one asset marker.

A source comparison reconstructs all four bodies from the v326 Git commit and
verifies an exact case-sensitive match after indentation and line-ending
normalization. Node syntax checking and collectstatic dry-run both pass.

## Audit state

The asset-boundary command now reports:

- zero inline style blocks and zero inline script blocks;
- one static CSS asset and one static JavaScript asset;
- zero inline event handlers and four inline `style=` attributes;
- zero legacy source-contract tests and fifteen asset-aware consumers;
- `mechanically_extractable=true`, `cutover_ready=true`, and
  `strict_csp_ready=false`.

The script scanner explicitly excludes external `src` tags, preventing the
empty external include from being misclassified as an inline script.

## Regression repairs

The first combined compatibility run found two tests whose multiline strings
encoded the old template indentation. The lightbox cancel listener and
location-copy textarea behavior were present in the static asset. Their tests
now assert stable behavior tokens instead of incidental leading whitespace.

## Validation evidence

- 31 combined v324-v327 source, audit, and response tests passed;
- 36 focused v317-v319, v322, and v327 interaction tests passed after the
  whitespace-contract repair;
- 166 combined v69, v72, v271-v275, v283, v317-v319, and v321-v327
  compatibility tests passed;
- the complete PostgreSQL suite passed with 2,899 tests in 414.096 seconds;
- Django system and template checks passed;
- `makemigrations --check --dry-run` reported no changes;
- collectstatic dry-run and Node syntax checking passed;
- the extracted JavaScript matched the normalized v326 sources exactly;
- `git diff --check` reported no whitespace errors before staging.

The expected complete-suite warnings exercise deliberate 4xx,
provider-failure, and permission-denied paths; the run ended with an explicit
`OK`.

## Repository and migration scope

V327 adds one static JavaScript asset and one regression module, replaces four
inline script blocks with one external include, updates the read-only audit and
asset-aware test expectations, repairs two indentation-sensitive tests, and
updates documentation. It adds no model, migration, package, service, secret,
generated artifact, or development-database mutation.

Checkpoint tag:

    project-checkpoint-v327-listing-detail-javascript-static-asset

The annotated tag resolves the exact checkpoint commit.

## Next milestone

V328 replaces the four remaining listing-detail inline `style=` attributes
with CSS classes and makes the audit distinguish template-owned CSP readiness
from inherited base-template inline assets.
