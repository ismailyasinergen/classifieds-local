# Price-Drop Public Browse Filter — v278

## Purpose

v278 adds a Price drops only option to the public listing browse page.

The filter returns listings whose newest real price transition is a reduction
and whose transition price still matches the current stored listing price.

## Query parameter

The filter uses price_drops=1.

Only the exact value 1 enables the filter.

## Compatibility

The implementation preserves existing keyword, location, category, price,
attribute, sorting, pagination, visibility, and saved-search behavior.

## Schema

v278 adds no model, migration, database field, URL, or background task.
