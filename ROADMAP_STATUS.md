# Roadmap Status

## Current stable product state

- Latest product milestone: **v323 — Staff CSV formula-neutralization**
- Product checkpoint:
  `project-checkpoint-v323-staff-csv-formula-neutralization`
- Previous milestone:
  `project-checkpoint-v322-listing-detail-accessibility`
- Validated regression baseline: **2,868 tests passing**
- Full-suite mode: PostgreSQL `--parallel 4 --keepdb --noinput`, explicit `OK`
  in 395.933 seconds; 416.3 seconds measured wall-clock time
- Django system check: zero issues
- Migration state: no v323 migration; all existing migrations are applied
  through `accounts.0016` and `listings.0025`, with no model changes pending

v323 applies one idempotent spreadsheet-formula neutralization contract across
all five staff CSV producer families. Listing reports, moderation appeals and
ZIP summaries, Trust & Safety action/event logs, seller-store admin exports, and
saved-search audit exports now neutralize `=`, `+`, `-`, `@`, tab, and carriage
return prefixes without changing headers, ordering, filters, or authorization.

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
- Repair: preserved legacy listing-detail source-shape contracts after v285
- Repair R003: replaced a sequence-dependent bare numeric privacy assertion
  with explicit recipient-state exposure checks

## Planned sequence

The selected next milestone is **v324 — Listing-detail asset-extraction
groundwork**. Its scope is a source-shape and dependency contract for moving the
oversized inline listing-detail CSS and JavaScript into versioned static assets
without changing rendered behavior, CSP assumptions, loading order, or the
v275-v323 marker surface.

Audit backlog after v321:

- consolidate shadowed duplicate view definitions in the largest accounts and
  listings modules only through separately tested extraction milestones after
  the listing-detail asset boundary is established.

Each numbered milestone requires focused tests, related compatibility tests,
Django checks, migration review, and a complete regression run before release.

The local development database is fully migrated through `accounts.0016` and
`listings.0025`. V323 did not run `migrate`; this statement records the observed
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
