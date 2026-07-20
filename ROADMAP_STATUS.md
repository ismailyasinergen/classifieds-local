# Roadmap Status

## Current stable product state

- Latest product milestone: **v302 — Unapplied migration deployment preflight**
- Product checkpoint:
  `project-checkpoint-v302-unapplied-migration-deployment-preflight`
- Previous milestone: `project-checkpoint-v301-notification-scheduler-leasing`
- Validated regression baseline: **2,663 tests passing**
- Full-suite mode: serial `--keepdb`, explicit `OK` in 1408.896 seconds
- Django system check: zero issues
- Migration state: no v302 migration; additive migration
  `0023_listingpricehistory_discount_guardrail_v293` remains the latest and no
  model changes are pending

The preserved, fully migrated serial test database passed the complete v302
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
- v300: read-only v296-v299 sprint closeout, 43-contract package audit,
  documentation verification, final system and migration checks, and complete
  2,641-test regression validation
- v301: PostgreSQL session advisory-lock coordination for listing-price-alert
  and saved-search notification schedulers, including cross-command exclusion,
  read-only-mode bypass, automatic connection-close recovery, sanitized busy
  output, and preservation of v287 event-level delivery claims
- v302: fail-closed production migration verification, explicit
  operator-controlled production migration application, preserved local
  auto-migration behavior, production preflight integration, rollback-safe
  operating guidance, and repository-enforced LF shell portability
- Repair: preserved legacy listing-detail source-shape contracts after v285
- Repair R003: replaced a sequence-dependent bare numeric privacy assertion
  with explicit recipient-state exposure checks

## Planned sequence

No numbered milestone is currently selected. The next milestone must be
chosen explicitly before implementation.

Verified-recipient policy, provider bounce handling, event retention, operator
recipient-output policy, and parallel preserved-test-database lifecycle work
remain explicit recommendations. Verified-recipient enforcement, provider
outcome ingestion, and retention automation remain deferred until their product,
provider, legal, and privacy policies are defined.

R009 scheduler-level leasing was completed in v301. PostgreSQL session advisory
locks now coordinate mutating and delivery-capable notification scheduler modes
without replacing the durable v287 logical-event claim boundary.

R014 unapplied-migration deployment preflight was completed in v302. Production
startup now defaults to a read-only, fail-closed migration check, while schema
application remains an explicit operator-controlled action. Local Compose
continues to apply migrations automatically.

Each numbered milestone requires focused tests, related compatibility tests,
Django checks, migration review, and a complete regression run before release.

The local development database was observed fully migrated through listings
migration `0023_listingpricehistory_discount_guardrail_v293` during v302
validation. v302 did not run `migrate`; this statement records the observed
database state only. The preserved Django test database is also fully migrated.

## Validation commands

```bash
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py check
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py makemigrations --check --dry-run
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py migrate --check --noinput
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py test --keepdb --verbosity 1
```

Use a serial test fallback when parallel database cloning or isolation—not product
behavior—is the failure source. An explicit final `OK` is mandatory.
