# v185 Category Seed Apply Workflow and Admin Verification

V185_CATEGORY_SEED_APPLY_ADMIN_VERIFICATION

## Purpose

v185 verifies that the expanded v184 category taxonomy can be applied safely to the local database and then verified before category navigation or listing-filter UI changes begin.

## What v185 adds

- A verification module for the expanded 100-category plan.
- A verify_marketplace_category_seed management command.
- A --require-applied mode that fails when the seed has not been applied.
- Admin verification for Category registration and safe hierarchy fields.
- Tests proving verification fails before apply and passes after apply.
- Local workflow checks that apply and verify the expanded taxonomy.

## Local commands

Apply the expanded taxonomy:

    docker compose exec web python manage.py seed_marketplace_categories_expanded --apply

Verify the local database:

    docker compose exec web python manage.py verify_marketplace_category_seed --require-applied

## Guardrails

- v185 does not change the v183 pilot plan.
- v185 does not change the v184 expanded plan.
- v185 does not change listing UI, listing filters, saved searches, or seller store behavior.
- v185 should generate no migrations.
- backend/docs/ must not be recreated.
- Full regression must pass before commit/tag.

## Recommended next checkpoints

- v186: category navigation and listing filter integration.
- v187: saved search category compatibility polish.
- v188: seller store category compatibility polish.
