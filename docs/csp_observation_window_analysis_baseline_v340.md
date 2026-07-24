# CSP observation-window analysis baseline v340

## Outcome

V340 adds a standalone, closeout-gated analyzer for one bounded window of
sanitized V337 CSP evidence.

Example:

    python backend/scripts/analyze_csp_observation_window_v340.py --closeout-json <v339-closeout.json> --window-start <inclusive-start> --window-end <exclusive-end> --json --strict < <sanitized-v337-window.jsonl>

The analyzer requires a fully ready V339 closeout result before observation
records are summarized. Real V339 CLI JSON produced with `sort_keys=True` is
accepted. Missing, extra, malformed, forged, or not-ready closeout fields fail
closed.

## Input contract

Standard input contains newline-delimited JSON. Every non-empty line must
contain exactly:

- `observed_at`;
- `event`;
- `schema_version`;
- `evidence`.

`observed_at` must be timezone-aware. `event` and `schema_version` must match
the V337 logging contract. `evidence` must contain the exact sanitized V337
key set and pass the V337 fail-closed validator.

V340 does not parse raw browser reports, raw request bodies, Docker log
prefixes, arbitrary application logs, or external collector formats. An
approved bounded export must add `observed_at` and preserve the standalone
sanitized V337 JSON object without adding raw fields.

## Bounds and deterministic summaries

The analyzer enforces:

- at most 1 MiB of JSONL input;
- at most 10,000 records;
- at most 128 KiB for the V339 closeout JSON;
- a minimum window of 60 seconds;
- a maximum window of exactly seven days;
- an inclusive start and exclusive end;
- at most eight buckets in each summary.

Summaries cover:

- effective directive;
- blocked-resource class;
- disposition;
- media type;
- HTTP status-code class.

Buckets are ordered by descending count and then lexical value. Cardinality
overflow is combined under collision-safe `__other__`. Absolute HTTP and
HTTPS resources become `origin`; scheme resources become `scheme`.

## Synthetic and organic evidence

V338 smoke observations use invented origins matching
`https://v338-<16-lowercase-hex>.invalid`. V340 counts these separately from
organic observations.

An empty window returns `analysis_ready` plus `no_records_in_window`. A
synthetic-only window returns `analysis_ready` plus `synthetic_only_window`.
These are structurally valid analyses, not proof that a deployment is ready
for CSP enforcement.

## Privacy and side-effect boundary

V340 output never includes:

- document or source origins;
- blocked-resource hostnames;
- URL paths, queries, fragments, or credentials;
- raw report bodies;
- script samples;
- input file content or input paths.

The implementation performs no network activity, persistence, database
access, subprocess execution, Docker operation, environment mutation, CSP
gate change, enforcement change, or automatic operational decision.

V340 does not authenticate collector exports, prove timestamps, establish
deployment identity, verify multi-node completeness, detect missing collector
events, or replace operator review.

## Scope

Changed files:

- `backend/scripts/analyze_csp_observation_window_v340.py`
- `backend/config/tests/test_csp_observation_window_analysis_v340.py`
- `docs/csp_observation_window_analysis_baseline_v340.md`
- `README_PRODUCTION.md`
- `ROADMAP_STATUS.md`

No model, migration, route, view, middleware, setting, template, static asset,
Nginx rule, Compose service, production environment default, CSP gate, or
enforcement behavior changed.

## Validation

- Fourteen V340 focused tests passed.
- The combined V337-V340 package passed 53 tests in 0.736 seconds.
- Real V339 `sort_keys=True` JSON compatibility is covered.
- Fractional seven-day overflow is covered.
- Summary-bucket collision is covered.
- `manage.py check` reported zero issues.
- `makemigrations --check --dry-run` detected no changes.
- No migration was created or applied.
- The development database was not mutated.

- Final PostgreSQL regression: 3,053 tests passed in 441.063 seconds.
- Measured full-regression wall-clock time: 474 seconds.
- The preserved base test database and all four parallel worker clones were
  retained.

Planned checkpoint:
`project-checkpoint-v340-csp-observation-window-analysis`.

The selected follow-up is v341, a bounded operator-facing review-decision
baseline over one approved V340 summary, without automatic enforcement or
configuration mutation.
