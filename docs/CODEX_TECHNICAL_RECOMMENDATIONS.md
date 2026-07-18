# Codex Technical Recommendations

This register records repository-backed engineering recommendations. Priorities
reflect current evidence rather than a generic wishlist.

## R001 — Validate listing-action return URLs (P1)

- **Category:** Security, correctness
- **Evidence:** `listing_favorite_views.py` redirected directly to the POSTed
  `next` value, allowing an authenticated action to end at an external host.
- **Affected systems:** Listing favorite and future listing-action POST views.
- **Value:** Prevents phishing-style open redirects while preserving local
  return-to-page behavior; centralizes a reusable safety rule.
- **Risk if ignored:** Trusted marketplace URLs could bounce users to an
  attacker-controlled site.
- **Effort / implementation risk:** Small / low.
- **Dependencies / order:** None; apply before adding more listing actions.
- **Validation:** External, scheme-relative, and same-origin redirect tests.
- **Status:** Implemented in repair R001.

## R002 — Restore a current roadmap source of truth (P1)

- **Category:** Documentation, operations
- **Evidence:** `ROADMAP_STATUS.md` still reports `project-checkpoint-v1` while
  Git is complete through v284; `AGENTS.md` also contains intentionally durable
  but older checkpoint examples.
- **Affected systems:** Contributor onboarding and release coordination.
- **Value:** Reduces incorrect recovery and checkpoint decisions.
- **Risk if ignored:** A future maintainer may target or repair the wrong state.
- **Effort / implementation risk:** Small / low.
- **Dependencies / order:** Update after the current sprint is finalized.
- **Validation:** Compare the document with Git tags, HEAD, and test results.
- **Status:** Implemented in documentation repair R002 after the v286 full-suite
  result was verified.

## R003 — Add durable notification-event deduplication (P1)

- **Category:** Correctness, database, privacy
- **Evidence:** Saved searches advance a checked timestamp after successful
  delivery, but listing-specific alerts have no event ledger yet. Retry and
  partial-failure behavior needs an idempotent listing/transition recipient key.
- **Affected systems:** Listing alerts and saved-search price-drop delivery.
- **Value:** Prevents duplicate email and supplies an auditable delivery state.
- **Risk if ignored:** Retries can repeatedly notify users or obscure failures.
- **Effort / implementation risk:** Medium / medium.
- **Dependencies / order:** v285 subscriptions and v286 matching; implement in
  the planned v287 deduplication milestone.
- **Validation:** Concurrent/retry tests and unique-constraint coverage.
- **Status:** Deferred to v287 to avoid pre-empting its schema contract.

## R004 — Benchmark price-history correlated subqueries (P2)

- **Category:** Performance, database
- **Evidence:** v278–v284 intentionally reuse annotations and avoid N+1 work,
  but PostgreSQL may inline correlated history expressions and no production-size
  `EXPLAIN ANALYZE` evidence is stored in the repository.
- **Affected systems:** Public browse, category browse, cards, and alert matching.
- **Value:** Identifies whether a covering index or materialized current metric
  is justified before traffic grows.
- **Risk if ignored:** Browse and notification batches may degrade at scale.
- **Effort / implementation risk:** Medium / low for measurement; higher for a
  schema change.
- **Dependencies / order:** Representative production-like data; measure before
  proposing an index or denormalization.
- **Validation:** Capture query plans and latency across realistic cardinalities.
- **Status:** Deferred pending representative data.

## R005 — Define verified-recipient delivery policy (P1)

- **Category:** Security, privacy, operations
- **Evidence:** Notification delivery currently requires only a non-empty user
  email; the accounts app has no repository-visible verified-email field.
- **Affected systems:** Saved-search and listing-specific email notifications.
- **Value:** Reduces misdirected mail, abuse, and deliverability complaints.
- **Risk if ignored:** Unverified or mistyped addresses may receive marketplace
  activity details.
- **Effort / implementation risk:** Medium / medium.
- **Dependencies / order:** Product policy and v288 delivery preferences.
- **Validation:** Verification-state, opt-in, unsubscribe, and privacy tests.
- **Status:** Deferred because recipient-verification policy requires a product
  decision; do not broaden delivery automatically.

## R006 — Make preserved parallel test clones migration-aware (P2)

- **Category:** Testing, operations
- **Evidence:** The post-v286 parallel `--keepdb` run discovered all 2,462 tests
  but worker clones lacked migration 0019; the migrated serial database passed
  the full suite with explicit `OK`.
- **Affected systems:** Django test database lifecycle and local/CI runbooks.
- **Value:** Restores fast parallel regression runs after schema milestones
  without unsafe manual database deletion.
- **Risk if ignored:** Parallel runs can report false product failures or force
  repeated eleven-minute serial validation.
- **Effort / implementation risk:** Small to medium / low if confined to test
  infrastructure.
- **Dependencies / order:** Inspect the Compose PostgreSQL clone lifecycle and
  choose a noninteractive, migration-aware refresh strategy before v287.
- **Validation:** Create a migration on a disposable branch, run parallel
  `--keepdb`, and prove all worker schemas update without losing non-test data.
- **Status:** Deferred; this sprint deliberately preserved existing databases
  and used the safe serial fallback.
