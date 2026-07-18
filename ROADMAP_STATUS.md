# Roadmap Status

## Current stable product state

- Latest product milestone: **v286 — Saved-search price-drop notifications**
- Product checkpoint: `project-checkpoint-v286-saved-search-price-drop-notifications`
- Previous milestone: `project-checkpoint-v285-listing-specific-price-alerts`
- Validated regression baseline: **2,462 tests passing**
- Full-suite mode: serial `--keepdb` fallback, explicit `OK` in 682.923 seconds
- Django system check: zero issues
- Migration state: migration `0019_listingpricealert` is committed; no pending model changes

The parallel full-suite attempt discovered all 2,462 tests but its preserved clone
databases predated migration 0019. The migrated serial database passed. See R006
in `docs/CODEX_TECHNICAL_RECOMMENDATIONS.md`.

## Recently completed

- v275–v282: price history, current-drop discovery, public filters, and sorting
- v283: public listing price-history timeline
- v284: accessible listing-card discount presentation
- R001: same-origin return URL validation for listing actions
- v285: listing-specific alert subscription, matching, and bounded email delivery
- v286: saved-search matching for newly reduced listings
- Repair: preserved legacy listing-detail source-shape contracts after v285

## Planned sequence

1. v287 — Notification deduplication
2. v288 — Notification delivery preferences and verified-recipient policy
3. v289 — Price-alert management UI
4. v290–v295 — Seller pricing and pricing-integrity controls
5. v296–v300 — Deals discovery, comparison/SEO integration, and release audit

Each numbered milestone requires focused tests, related compatibility tests,
Django checks, migration review, and a complete regression run before release.

## Validation commands

```bash
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py check
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py makemigrations --check --dry-run
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 web python manage.py test --parallel 4 --keepdb --verbosity 1
```

Use a serial test fallback when parallel database cloning or isolation—not product
behavior—is the failure source. An explicit final `OK` is mandatory.
