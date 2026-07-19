# v300 — Public Deals sprint closeout and final audit

## Purpose

v300 closes the Public Deals sprint delivered through v296-v299.

This milestone is a read-only release and documentation audit. It introduces
no new buyer-facing behavior and does not redefine deal eligibility, discount
ordering, listing comparison, metadata, navigation, or accessibility behavior.

## Sprint summary

The completed sprint contains:

- v296 — public, paginated Deals discovery using the established discount and
  public-visibility contracts;
- v297 — deal-aware listing comparison with shared buyer-facing discount
  evidence and direct Deals discovery links;
- v298 — normalized canonical metadata, robots directives, Open Graph,
  Twitter metadata, and safe CollectionPage JSON-LD;
- v299 — shared-header integration, active-page semantics, keyboard focus,
  discovery continuity, and release-readiness coverage.

The four milestone modules contain 43 existing milestone tests before the new
v300 closeout audit is added.

## Closeout validation contract

The v300 audit confirms that:

- all v296-v299 milestone markers remain enabled;
- `/deals/` still resolves to the single established v296 view;
- the 43 existing milestone tests remain packaged;
- pagination, deterministic ordering, stable query counts, comparison evidence,
  canonical metadata, JSON-LD safety, active navigation, and accessibility
  contracts remain represented;
- all four milestone documents and implementation files remain present;
- header, comparison, and SEO surfaces share the same Deals route identity;
- migration
  `0023_listingpricehistory_discount_guardrail_v293.py`
  remains the latest listings migration.

Release verification requires focused v300 tests, the complete v296-v300
related package, the Django system check, the migration dry-run, and a complete
serial `--keepdb` regression with an explicit `OK`.

## Deliberate exclusions

- No new route
- No model change
- No migration
- No new pricing or deal-qualification algorithm
- No sitemap or robots endpoint
- No personalized recommendation or tracking feature
- No development-database migration application

## Release outcome

The completed v300 validation produced:

- 8 focused v300 audit tests passing;
- 51 related v296-v300 tests passing;
- Django system check with zero issues;
- migration dry-run with no changes detected;
- 2,641 full-regression tests passing in 1293.325 seconds using serial
  `--keepdb`;
- migration
  `0023_listingpricehistory_discount_guardrail_v293.py`
  remaining the latest listings migration.

The development database reported listings migrations `0019`-`0023` as
applied during final inspection. v300 did not execute `migrate`; this records
the observed state rather than a migration action performed by the milestone.

The v296-v299 Public Deals sprint is closed. No next numbered milestone is
currently selected; future work requires an explicit priority decision.
