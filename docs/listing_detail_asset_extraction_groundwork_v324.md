# v324 - Listing-detail asset-extraction groundwork

LISTING_DETAIL_ASSET_EXTRACTION_GROUNDWORK_V324=1

## Purpose

V324 establishes an executable, read-only boundary around the oversized inline
CSS and JavaScript in the listing-detail template. It records the current
source shape and the dependencies that must be preserved before a later
milestone moves code into versioned static assets.

This checkpoint does not extract assets, change browser loading order, tighten
Content Security Policy, or alter rendered listing behavior.

## Inventory contract

The audit currently records:

- one inline style block;
- four inline script blocks;
- five total asset blocks with no Django template syntax;
- two inline `onerror` image handlers;
- eleven tests that read `listing_detail.html` directly as a legacy source
  contract;
- the milestone markers owned by each block and the complete template marker
  surface.

Because none of the five asset blocks contains template syntax, they are
mechanically extractable. Cutover is intentionally reported as not ready while
inline event handlers and legacy source-reading contracts remain. Strict CSP
readiness is also false while any inline style, script, or event handler exists.

The planned asset paths are recorded, but are not created by this milestone:

    listings/listing-detail-v324.css
    listings/listing-detail-v324.js

## Operator interface

The audit is deterministic and read-only:

```bash
python manage.py audit_listing_detail_assets_v324
python manage.py audit_listing_detail_assets_v324 --json
python manage.py audit_listing_detail_assets_v324 --fail-on-blockers
```

The default output is concise for operators. JSON exposes block ranges,
character counts, template-syntax flags, marker ownership, inline handlers,
source-contract test paths, readiness booleans, and stable blocker codes.
`--fail-on-blockers` is CI-compatible and exits with a command error until the
identified blockers have been removed.

## Validation evidence

- 8 focused v324 tests passed;
- 139 combined v271-v275, v283, v317-v319, v321-v322, and v324 compatibility
  tests passed;
- the complete PostgreSQL suite passed with 2,876 tests in 416.325 seconds;
- Django system and template checks passed;
- `makemigrations --check --dry-run` reported no changes;
- `git diff --check` reported no whitespace errors before staging.

The expected complete-suite warnings exercise deliberate 4xx,
provider-failure, and permission-denied paths; the run ended with an explicit
`OK`.

## Repository and migration scope

V324 adds one audit module, one management command, one regression module, one
template marker, and documentation. It adds no static asset, runtime include,
model, migration, package, service, secret, generated artifact, or development
database mutation.

Checkpoint tag:

    project-checkpoint-v324-listing-detail-asset-boundary

The annotated tag resolves the exact checkpoint commit.

## Next milestone

V325 removes the two inline image error handlers and gives legacy
source-contract tests an asset-aware source surface. Those changes clear the
explicit blockers before the physical CSS and JavaScript cutover.
