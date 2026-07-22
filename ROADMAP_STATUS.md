# Roadmap Status

## Current stable product state

- Latest product milestone: **v325 — Listing-detail extraction blocker removal**
- Product checkpoint:
  `project-checkpoint-v325-listing-detail-extraction-blockers`
- Previous milestone:
  `project-checkpoint-v324-listing-detail-asset-boundary`
- Validated regression baseline: **2,883 tests passing**
- Full-suite mode: PostgreSQL `--parallel 4 --keepdb --noinput`, explicit `OK`
  in 384.497 seconds; 406.2 seconds measured wall-clock time
- Django system check: zero issues
- Migration state: no v325 migration; all existing migrations are applied
  through `accounts.0016` and `listings.0025`, with no model changes pending

v325 replaces two inline image error handlers with equivalent early/late
failure listeners and migrates eleven legacy source-reading tests to a shared,
asset-aware contract. The audit now reports zero cutover blockers while keeping
strict CSP readiness false for the remaining inline blocks and style
attributes.

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
- v303: migration-aware PostgreSQL preserved worker-clone refresh, strict
  Django test-prefix and clone-name validation, fail-closed active-connection
  behavior, temporary test-only creation-object replacement, and unchanged
  serial, non-keepdb, non-PostgreSQL, and application-runtime behavior
- v304: read-only executable notification-delivery policy baseline covering
  verified-recipient state, provider outcomes, delivery-event retention and
  operator recipient output, with sanitized text/JSON reporting and no runtime
  enforcement, provider access, deletion automation or legacy-output rewrite
- v305: shared idempotent recipient-output redaction across explicit-send,
  preview, observability and rollback operator surfaces, preserving
  `<missing>` diagnostics, internal delivery destinations and all established
  sender, renderer and scheduler contracts
- v306–v316: verified-recipient lifecycle, provider outcomes, retention,
  enforcement, rollout controls, backup/restore verification, and completed
  development-database migration rollout
- v317: listing share and print actions
- v318: full-screen listing gallery lightbox
- v319: listing location map and copy actions
- v320: listing social preview and SEO metadata
- v321: mobile buyer action bar plus audit-driven buyer-action, redirect, and
  conversation query repairs
- v322: listing-detail accessibility audit covering skip navigation, semantic
  content order, headings, focus visibility, motion preferences, live regions,
  unique IDs, and modal gallery keyboard containment
- v323: shared, idempotent spreadsheet-formula neutralization across all staff
  CSV producer families with real export-response regression coverage
- v324: deterministic, read-only listing-detail asset boundary with block
  ranges, template-dependency and marker inventories, explicit CSP/cutover
  blockers, JSON output, and a CI-compatible failure mode
- v325: equivalent data-hook image fallbacks, asset-aware source contracts for
  eleven migrated test modules, zero extraction blockers, and inline-style
  inventory that prevents strict-CSP overclaiming
- Repair: preserved legacy listing-detail source-shape contracts after v285
- Repair R003: replaced a sequence-dependent bare numeric privacy assertion
  with explicit recipient-state exposure checks

## Planned sequence

The selected next milestone is **v326 — Listing-detail CSS static-asset
extraction**. Its scope is to move only the template-independent style block to
the planned versioned static file while preserving cascade order, template
markers, rendering, and the asset-aware test surface. JavaScript remains inline
for an independently validated later milestone.

Audit backlog after v321:

- consolidate shadowed duplicate view definitions in the largest accounts and
  listings modules only through separately tested extraction milestones after
  the listing-detail asset boundary is established.

Each numbered milestone requires focused tests, related compatibility tests,
Django checks, migration review, and a complete regression run before release.

The local development database is fully migrated through `accounts.0016` and
`listings.0025`. V325 did not run `migrate`; this statement records the observed
database state only. The preserved base test database and all four parallel
worker clones remain fully migrated.

## Validation commands

```bash
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py check
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py makemigrations --check --dry-run
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py migrate --check --noinput
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py check_notification_delivery_policy
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py test --parallel 4 --keepdb --noinput --verbosity 1
```

Parallel preserved-database validation is now the default complete regression
path. Use the serial `--keepdb` fallback only when a separate parallel isolation
or multiprocessing limitation is proven. An explicit final `OK` is mandatory.
