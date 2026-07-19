# Roadmap Status

## Current stable product state

- Latest product milestone: **v299 — Deals discovery integration and release-readiness audit**
- Product checkpoint: `project-checkpoint-v299-public-deals-discovery-integration-audit`
- Previous milestone: `project-checkpoint-v298-public-deals-seo-metadata`
- Validated regression baseline: **2,633 tests passing**
- Full-suite mode: serial `--keepdb`, explicit `OK` in 1220.745 seconds
- Django system check: zero issues
- Migration state: no v296, v297, v298, or v299 migration; additive migration
  `0023_listingpricehistory_discount_guardrail_v293` remains the latest and no
  model changes are pending

The preserved, fully migrated serial test database passed the complete v299
suite. Parallel preserved-database lifecycle limitations remain documented in
R006 of `docs/CODEX_TECHNICAL_RECOMMENDATIONS.md`.

## Recently completed

- v275–v282: price history, current-drop discovery, public filters, and sorting
- v283: public listing price-history timeline
- v284: accessible listing-card discount presentation
- R001: same-origin return URL validation for listing actions
- v285: listing-specific alert subscription, matching, and bounded email delivery
- v286: saved-search matching for newly reduced listings
- v287: durable logical delivery events, atomic claims, bounded retries, and
  duplicate suppression
- v288: independent defaults-on delivery preferences with terminal suppression
  and an authenticated settings page
- v289: authenticated, paginated management and owner-scoped removal for
  listing-specific price-alert subscriptions
- v290: owner-scoped seller pricing dashboard with bounded price-history
  annotations, deterministic sorting, status filtering, and direct edit links
- v291: signed, owner-only, stale-safe price-change review and confirmation
- v292: optional structured transition reasons with private seller-dashboard
  display and no public timeline disclosure
- v293: sequence-based raise-then-drop detection with durable reference prices,
  public discount suppression, seller warnings, and factual-history preservation
- v294: staff-only, read-only pricing-integrity evidence queue with bounded
  search, deterministic pagination, current/historical classification, and no
  enforcement actions
- v295: read-only two-query price-history consistency audit with bounded,
  sanitized text/JSON output and CI-compatible failure mode
- v296: public, paginated Deals discovery using established discount
  qualification, visibility, ordering, and listing-card contracts
- v297: deal-aware listing comparison with previous/current prices, savings,
  discount badges, and a direct Deals discovery link
- v298: request-aware Deals SEO metadata with deterministic canonicals,
  robots directives, Open Graph and Twitter tags, safe CollectionPage JSON-LD,
  and backward-compatible opt-in shared-head rendering
- v299: shared-header Deals active state, `aria-current` semantics, visible
  keyboard focus, discovery-flow continuity, and cross-milestone
  release-readiness audit
- Repair: preserved legacy listing-detail source-shape contracts after v285
- Repair R003: replaced a sequence-dependent bare numeric privacy assertion
  with explicit recipient-state exposure checks

## Planned sequence

1. v300 — v296–v299 sprint closeout, final verification, and roadmap refresh

Verified-recipient policy, provider bounce handling, event retention, and
scheduler leasing remain explicit recommendations rather than hidden v289
scope. Verified-recipient enforcement and retention automation remain deferred
until their product and privacy policies are defined.

Each numbered milestone requires focused tests, related compatibility tests,
Django checks, migration review, and a complete regression run before release.

The current local development database has listings migrations `0019`–`0023`
pending and remained deliberately unmodified through v299 validation.
Operational commands that use post-v286 fields require those committed
migrations to be applied first. The preserved Django test database is fully
migrated.

## Validation commands

```bash
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py check
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py makemigrations --check --dry-run
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py test --keepdb --verbosity 1
```

Use a serial test fallback when parallel database cloning or isolation—not product
behavior—is the failure source. An explicit final `OK` is mandatory.
