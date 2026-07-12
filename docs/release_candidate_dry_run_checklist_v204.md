# v204 Release Candidate Dry-Run Checklist

V204_RELEASE_CANDIDATE_DRY_RUN_CHECKLIST

## Purpose

v204 is an audit-only release candidate dry-run checklist after the v203 Category admin template guidance checkpoint.

## Current checkpoint

- Current base before v204: `f4e8707`
- Current base tag: `project-checkpoint-v203-category-taxonomy-admin-template-guidance`
- v204 target tag: `project-checkpoint-v204-release-candidate-dry-run-checklist`

## Dry-run checklist

Before treating this branch as a release-candidate baseline, keep these checks green:

- `git status --short --untracked-files=all` is clean before patching.
- `backend/docs/` is absent and is not recreated.
- `python -m py_compile` passes for new/changed Python files.
- `docker compose exec web python manage.py check` passes.
- `docker compose exec web python manage.py makemigrations --check --dry-run` reports no changes.
- `docker compose exec web python manage.py verify_marketplace_category_seed --require-applied` passes.
- Category seed verification keeps `Admin fields OK: True`.
- v203 Category admin template guidance tests pass.
- v202 saved-search notification behavior contract audit tests pass.
- v201 seller-store public accessibility tests pass.
- Category admin/navigation regression guard passes.
- Saved-search regression guard passes.
- Seller-store public + directory regression guard passes.
- Full Django regression passes before commit/tag.
- Only v204 audit files are staged.
- `git diff --cached --check` passes.

## Release-candidate surfaces covered

v204 checks these current release-candidate surfaces:

- Category admin contracts from v196, v199, and v203.
- Category admin changelist template guidance from v203.
- Saved-search notification contract from v197 and v202.
- Seller-store public responsiveness/accessibility from v198 and v201.
- Seller-store directory responsiveness from v195.
- Public category navigation accessibility from v193.
- Project milestone audit state from v200.

## Scope boundaries

v204 intentionally does not change runtime behavior.

It does not change:

- Models.
- Migrations.
- Forms.
- URLs.
- Views.
- Templates.
- Category admin behavior.
- Saved-search behavior.
- Seller-store behavior.
- Public category navigation behavior.

This is a release-candidate dry-run checklist checkpoint only.

## Expected committed files

- `backend/listings/test_release_candidate_dry_run_checklist_v204.py`
- `docs/release_candidate_dry_run_checklist_v204.md`

## Next recommended lanes

- v205: saved-search notification UI accessibility polish, if needed.
- v206: seller-store admin/detail polish audit, if needed.
- v207: release candidate final hardening audit, if needed.
