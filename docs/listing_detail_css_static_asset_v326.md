# v326 - Listing-detail CSS static asset

LISTING_DETAIL_CSS_STATIC_ASSET_V326=1

## Purpose

V326 moves the single template-independent listing-detail style block into the
planned versioned static CSS file. JavaScript remains inline and its execution
order is unchanged.

The extraction does not redesign the page, change selectors, alter cascade
order, tighten CSP, or mutate application data.

## Static loading contract

The shared base template now exposes an empty-by-default `extra_styles` block
immediately before `</head>`. The listing-detail template extends that block
with exactly one Django static link:

    /static/listings/listing-detail-v324.css

The file is discoverable through Django staticfiles and collectstatic dry-run.
A real approved-listing response verifies that the link is rendered once and
inside the document head.

## Extraction integrity

The original v325 inline style body contained 33,289 characters including
template indentation. V326 removes only that common indentation and adds one
asset marker, producing a 24,699-character CSS file.

A source comparison reconstructs the style body from the v325 Git commit,
normalizes only the removed indentation and line endings, and verifies an exact
case-sensitive match with the new asset. All eight style-owned milestone
markers remain in the CSS file.

## Audit state

The asset-boundary command now distinguishes inline blocks from physical static
assets. Its v326 state is:

- zero inline style blocks;
- four inline script blocks;
- one static CSS asset and no static JavaScript asset;
- zero inline event handlers and four inline `style=` attributes;
- zero legacy source-contract tests and fourteen asset-aware consumers;
- `cutover_ready=true` and `strict_csp_ready=false`.

The shared v325 source reader now returns the template followed by the CSS
asset, so existing marker and selector tests remain stable across extraction.

## Regression repair

The first complete-suite run exposed a legacy v69 response assertion that had
been passing for the wrong reason: it found a generic-grid selector and the v69
marker inside the old inline CSS, even when the current v72 vehicle panel was
rendered. V326 moves the marker assertion to the asset-aware source and verifies
the actual specialized vehicle response. The focused v69/v72/V326 repair
package passed before the complete suite was rerun.

## Validation evidence

- 22 combined v324-v326 source/audit tests passed before the final render test;
- all 8 v326 tests, including the real response integration test, passed;
- 154 combined v271-v275, v283, v317-v319, and v321-v326 compatibility tests
  passed;
- the focused v69, v72, and v326 repair package passed 12 tests;
- the final complete PostgreSQL suite passed with 2,891 tests in 397.561
  seconds;
- Django system and template checks passed;
- `makemigrations --check --dry-run` reported no changes;
- collectstatic dry-run passed;
- the extracted CSS matched the normalized v325 source exactly;
- `git diff --check` reported no whitespace errors before staging.

The expected complete-suite warnings exercise deliberate 4xx,
provider-failure, and permission-denied paths; the final run ended with an
explicit `OK`.

## Repository and migration scope

V326 adds one static CSS asset and one regression module, adds the shared head
extension point, updates the listing-detail template and read-only audit,
repairs one legacy response-source test, and updates documentation. It adds no
model, migration, package, service, secret, generated artifact, or
development-database mutation.

Checkpoint tag:

    project-checkpoint-v326-listing-detail-css-static-asset

The annotated tag resolves the exact checkpoint commit.

## Next milestone

V327 extracts the four template-independent listing-detail scripts into the
planned static JavaScript file at the same bottom-of-page execution point.
