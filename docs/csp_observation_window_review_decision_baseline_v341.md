# CSP observation-window review-decision baseline v341

## Outcome

V341 adds a standalone, operator-facing review decision over one approved V340
CSP observation-window summary.

Example:

    python backend/scripts/review_csp_observation_window_v341.py --summary-json <v340-summary.json> --json --strict

The result is advisory. It does not enable CSP enforcement, change a rollout
gate, mutate configuration, or perform an automatic operational action.

## Input contract

V341 accepts one JSON document produced by the V340 observation-window
analyzer.

The input must contain the exact V340 result key set and must report:

- marker `CSP_OBSERVATION_WINDOW_ANALYSIS_V340`;
- status `ready`;
- `ready=true`;
- `read_only=true`;
- `network_activity=false`;
- `persistence=false`;
- `enforcement=false`;
- canonical UTC window timestamps;
- internally consistent record counts;
- exact V340 reason-code semantics;
- five valid bounded summaries.

Missing, extra, malformed, forged, inconsistent, or not-ready fields fail
closed as `summary_invalid`.

The summary JSON is limited to 128 KiB. Missing, unreadable, malformed UTF-8,
invalid JSON, and oversized files return explicit fail-closed reason codes.

## Fixed review thresholds

V341 uses fixed thresholds:

- minimum observation window: 86,400 seconds;
- minimum organic observations: 25;
- maximum synthetic observations: 0.

The thresholds are emitted in every result so an operator can see the exact
basis of the recommendation.

## Deterministic decision model

V341 returns one of the following outcomes:

- invalid input:
  `not_ready / reject_summary / summary_invalid`;
- unreadable input:
  `not_ready / reject_summary / summary_input_unreadable`;
- oversized input:
  `not_ready / reject_summary / summary_input_too_large`;
- window below 24 hours:
  `insufficient_evidence / continue_observation /
  window_too_short_for_review`;
- empty window:
  `insufficient_evidence / continue_observation /
  no_records_in_window`;
- synthetic-only window:
  `insufficient_evidence / continue_observation /
  synthetic_only_window`;
- mixed synthetic and organic window:
  `insufficient_evidence / continue_observation /
  synthetic_records_present`;
- fewer than 25 clean organic observations:
  `insufficient_evidence / continue_observation /
  organic_record_count_below_threshold`;
- threshold-complete clean organic window:
  `ready / review_clean_organic_findings / review_ready`.

A `ready` result means only that the bounded summary is ready for human review.
It is not an enforcement approval.

## Result and CLI contract

Every result contains a fixed 22-key structure covering:

- source marker;
- status, readiness, recommendation, and reason codes;
- fixed review thresholds;
- source window boundaries and record counts;
- explicit side-effect guarantees.

The output always reports:

- `automatic_action=false`;
- `read_only=true`;
- `network_activity=false`;
- `persistence=false`;
- `enforcement=false`;
- `gate_change=false`;
- `configuration_mutation=false`.

`--json` emits compact deterministic JSON with sorted keys.

`--strict` exits non-zero unless the review result is `ready`. Without
`--strict`, the command reports the result without converting an
insufficient-evidence outcome into a shell failure.

## Privacy and side-effect boundary

V341 does not emit or inspect:

- raw CSP reports;
- origins, hostnames, paths, queries, fragments, or credentials;
- script samples;
- individual observation records;
- V340 summary bucket values in operator text output.

The implementation performs no network activity, database access, persistence,
subprocess execution, Docker operation, environment mutation, CSP gate change,
configuration mutation, enforcement action, or automatic deployment decision.

V341 does not prove collector completeness, deployment identity, multi-node
coverage, timestamp authenticity, or the operational safety of enabling CSP
enforcement.

## Scope

Changed files planned for V341:

- `backend/scripts/review_csp_observation_window_v341.py`;
- `backend/config/tests/test_csp_observation_window_review_v341.py`;
- `docs/csp_observation_window_review_decision_baseline_v341.md`;
- `README_PRODUCTION.md`;
- `ROADMAP_STATUS.md`.

No model, migration, route, view, middleware, setting, template, static asset,
Nginx rule, Compose service, production environment default, CSP gate, or
enforcement behavior changes.

## Validation

- Twelve V341 focused tests passed.
- The combined V340-V341 adjacent package passed 26 tests.
- The complete V337-V341 CSP package passed 65 tests in 0.787 seconds.
- Final PostgreSQL regression: 3,065 tests passed in 450.755 seconds.
- Measured full-regression wall-clock time: 489 seconds.
- Django system checks reported zero issues.
- `makemigrations --check --dry-run` detected no changes.
- Source structure checks found no duplicate top-level definitions.
- Static safety scanning found no network, subprocess, environment, or database
  mutation patterns.
- No migration was created or applied.
- The development database was not mutated.
- The preserved base test database and all four parallel worker clones were
  retained.

Source hashes at this validation point:

- V341 script:
  `b45ccb2cea5518b0703201dd14a82f9ec26c4126d7770dd37472000f10ccd5b5`;
- V341 tests:
  `c52662364dad10490c9e399029d52cd3017614c9891fda2b86ffed7604668100`.

Planned checkpoint:
`project-checkpoint-v341-csp-observation-window-review-decision`.
