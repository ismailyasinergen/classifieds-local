# Roadmap Status

## Current stable product state

- Latest product milestone: **v295 — Price-history integrity audit**
- Product checkpoint: `project-checkpoint-v295-price-history-integrity-audit`
- Previous milestone: `project-checkpoint-v294-pricing-integrity-moderation-queue`
- Validated regression baseline: **2,590 tests passing**
- Full-suite mode: serial `--keepdb`, explicit `OK` in 808.525 seconds
- Django system check: zero issues
- Migration state: no v294 migration; additive migration
  `0023_listingpricehistory_discount_guardrail_v293` remains the latest and no
  model changes are pending

The non-`keepdb` parallel attempt discovered all 2,495 tests but stopped before
execution because the preserved base test database already existed and Django
requested interactive deletion. No database was deleted. The migrated serial
database passed. See R006 in `docs/CODEX_TECHNICAL_RECOMMENDATIONS.md`.

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
- Repair: preserved legacy listing-detail source-shape contracts after v285
- Repair R003: replaced a sequence-dependent bare numeric privacy assertion
  with explicit recipient-state exposure checks

## Planned sequence

1. v296–v300 — Deals discovery, comparison/SEO integration, and release audit

Verified-recipient policy, provider bounce handling, event retention, and
scheduler leasing remain explicit recommendations rather than hidden v289
scope. Verified-recipient enforcement and retention automation remain deferred
until their product and privacy policies are defined.

Each numbered milestone requires focused tests, related compatibility tests,
Django checks, migration review, and a complete regression run before release.

The current local development database has listings migrations `0019`–`0023`
pending and was deliberately not mutated during v295 validation. Operational
commands that use post-v286 fields require those committed migrations to be
applied first. The preserved Django test database is fully migrated.

## Validation commands

```bash
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py check
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py makemigrations --check --dry-run
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py test --keepdb --verbosity 1
```

Use a serial test fallback when parallel database cloning or isolation—not product
behavior—is the failure source. An explicit final `OK` is mandatory.
