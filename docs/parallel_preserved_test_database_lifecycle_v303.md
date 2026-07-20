# Parallel preserved test database lifecycle — v303

## Purpose

v303 closes R006 by making Django's preserved PostgreSQL worker clones
migration-aware.

Django already migrates the preserved base test database during test setup.
Before v303, existing parallel worker clones could remain at an older migration
state because PostgreSQL `keepdb` clone setup reused them without replacing or
migrating them.

## Runtime boundary

The project configures:

    TEST_RUNNER = "config.test_runner.MigrationAwareParallelDiscoverRunner"

The custom runner changes database creation behavior only when both conditions
are true:

- `--parallel` resolves to more than one worker;
- `--keepdb` is enabled.

Serial runs, parallel runs without `--keepdb`, non-PostgreSQL connections, and
normal application runtime retain Django's default behavior.

## Refresh sequence

For each PostgreSQL database alias used by the suite:

1. Django creates or reuses and migrates the preserved base test database.
2. The temporary creation class validates the base and target names.
3. Each expected worker clone is dropped without force-disconnecting sessions.
4. The worker clone is recreated using the migrated base test database as its
   PostgreSQL template.
5. Django runs the test suite against the refreshed clones.
6. The original database creation object is restored after setup, including
   when setup raises an exception.

## Safety controls

Clone refresh requires all of the following:

- the source database begins with Django's `test_` prefix;
- the worker suffix is a positive integer;
- the target is exactly the source name plus that numeric suffix;
- the target also begins with the `test_` prefix.

The implementation does not use PostgreSQL `WITH (FORCE)`. An active worker
connection therefore causes refresh to fail safely rather than terminating a
possibly concurrent test process.

The implementation never targets the development database or the preserved base
test database for deletion.

## Validation evidence

The v303 candidate recorded:

- 10 focused lifecycle tests passing;
- a 66-test parallel smoke suite passing in approximately 14 seconds;
- all four stale worker clones recreated from the migrated base;
- development and base test database OIDs remaining unchanged;
- worker migration counts matching the base migration count;
- all workers containing listings migration
  `0023_listingpricehistory_discount_guardrail_v293`;
- the complete parallel regression discovering and running 2,673 tests;
- explicit full-suite `OK` in 362.498 seconds;
- 382 seconds measured wall-clock time;
- Django system checks with zero issues;
- `makemigrations --check --dry-run` reporting no changes;
- `migrate --check --noinput` passing against the development database.

Expected permission-denied tests may emit Django warning tracebacks while still
passing. Full-suite success is determined by the unittest summary, executed test
count, process exit status, and explicit final `OK`, not by the mere presence of
a logged traceback.

## Scope

v303 adds no model, schema migration, route, view, template, background worker,
production database backend, or application data mutation.
