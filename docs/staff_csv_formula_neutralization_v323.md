# v323 — Staff CSV formula-neutralization

STAFF_CSV_FORMULA_NEUTRALIZATION_V323=1

## Purpose

V323 closes the remaining spreadsheet-formula injection risk in staff-only CSV
downloads and replaces two local implementations with one shared, idempotent
cell-safety contract.

The checkpoint does not change which users can export data, which records are
selected, or which columns are included.

## Producer inventory

The repository contains five staff CSV producer families:

- seller-store Django admin review export;
- moderation-appeal export and ZIP summary CSV;
- Trust & Safety action-log and event-log exports;
- listing-report export;
- saved-search notification audit export.

Seller-store and saved-search exports already had local `=`, `+`, `-`, and `@`
guards. Listing-report, appeal, and Trust & Safety rows were unguarded. V323
routes every family through `config.csv_safety_v323` while preserving the two
legacy helper names for compatibility.

## Safety contract

`csv_safe_cell_v323` converts `None` to an empty cell and other values to their
normal string representation. If the first character is one of the following,
the helper prefixes one apostrophe:

    = + - @ TAB CR

Already neutralized values begin with an apostrophe and remain unchanged, so
the operation is idempotent. Ordinary values, headers, row ordering, content
types, filenames, filters, and authorization are unchanged.

Both sequence rows and `csv.DictWriter` mappings use the same helper through
`csv_safe_row_v323` and `write_csv_row_v323`.

## Regression evidence

The v323 tests create actual malicious model values and parse the downloaded CSV
responses to verify exact protected cell positions for:

- listing title, report details, reporter note, and admin note;
- appeal listing title, message, evidence-request note, decision note, and
  internal note;
- Trust & Safety action-log listing/message/decision/internal-note cells;
- Trust & Safety event title, listing title, public note, and internal note.

The suite also verifies all six prefixes, idempotence, ordinary values, mapping
rows, legacy helper delegation, shared-module adoption, and no v323 migration.

## Validation evidence

- 7 focused v323 tests passed;
- 101 combined v94, v96, v163-v164, v215, v233-v234, and v323 compatibility
  tests passed;
- the complete PostgreSQL suite passed with 2,868 tests in 395.933 seconds;
- Django system and template checks passed;
- `makemigrations --check --dry-run` reported no changes;
- `git diff --check` reported no whitespace errors before staging.

The expected complete-suite warnings exercise deliberate 4xx, provider-failure,
and permission-denied paths; the run ended with an explicit `OK`.

## Repository and migration scope

V323 adds one shared helper and one regression module, updates the five producer
families, and updates roadmap/documentation. It adds no model, migration,
package, service, secret, generated artifact, or development-database mutation.

Checkpoint tag:

    project-checkpoint-v323-staff-csv-formula-neutralization

The annotated tag resolves the exact checkpoint commit.

## Next milestone

V324 establishes the tested static-asset boundary needed to safely extract the
oversized inline listing-detail CSS and JavaScript.
