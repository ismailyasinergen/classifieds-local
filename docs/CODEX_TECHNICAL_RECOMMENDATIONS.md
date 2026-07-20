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
- **Evidence:** v287 added `NotificationDeliveryEvent`, deterministic logical
  keys, a database uniqueness constraint, short claims, bounded retries, and
  stale-claim recovery for all current notification paths.
- **Affected systems:** Listing alerts and saved-search email delivery.
- **Value:** Prevents duplicate email and supplies an auditable delivery state.
- **Risk if ignored:** Retries can repeatedly notify users or obscure failures.
- **Effort / implementation risk:** Medium / medium.
- **Dependencies / recommended order:** Completed after v285 and v286.
- **Validation:** Concurrent/retry tests and unique-constraint coverage.
- **Status:** Implemented in v287. External email still has a documented
  accepted-by-backend/mark-sent crash window because no provider idempotency
  key is available.

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
- **Dependencies / recommended order:** Product policy and the completed v288
  delivery preferences; decide before increasing notification volume.
- **Validation:** Verification-state, opt-in, unsubscribe, and privacy tests.
- **Status:** Policy baseline defined in v304; implementation remains open.
  The read-only capability check confirms that no repository-visible
  email-specific verification state exists. Runtime enforcement remains
  disabled, and the established non-empty-email rule is preserved until an
  address-bound verification lifecycle is designed and validated.

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
- **Dependencies / recommended order:** Inspect the Compose PostgreSQL clone lifecycle and
  choose a noninteractive, migration-aware refresh strategy before v287.
- **Validation:** Create a migration on a disposable branch, run parallel
  `--keepdb`, and prove all worker schemas update without losing non-test data.
- **Status:** Completed in v303. A test-only custom `DiscoverRunner` now
  temporarily installs migration-aware PostgreSQL creation handling only for
  parallel `--keepdb` setup. The migrated preserved base test database remains
  intact while validated worker clone names are dropped and recreated from that
  base. Clone names must use Django's test prefix and the exact positive numeric
  suffix contract. Active clone connections fail closed and are never forcibly
  terminated. Serial, non-keepdb, non-PostgreSQL, and application-runtime paths
  preserve Django defaults. The complete parallel regression passed all 2,673
  tests in 362.498 seconds.

## R007 — Integrate provider delivery and bounce outcomes (P1)

- **Category:** Correctness, observability, operations
- **Evidence:** Senders record synchronous backend exceptions and zero-delivery
  results, but the repository has no provider message ID, webhook, bounce, or
  complaint ingestion path.
- **Affected systems:** `NotificationDeliveryEvent`, email sender services, and
  notification operations.
- **User / business value:** Reduces repeated delivery to invalid addresses and
  makes support outcomes explainable.
- **Technical value:** Separates backend acceptance from actual delivery and
  supplies evidence for retry policy.
- **Risk if ignored:** Sent events can mask downstream bounces and reputation
  problems.
- **Effort / implementation risk:** Medium to large / medium.
- **Dependencies / recommended order:** Choose an email provider and privacy
  retention policy; address alongside R005 before high-volume rollout.
- **Validation:** Signed webhook, replay, ownership, bounce, complaint, and
  redacted-log tests.
- **Status:** Provider-outcome contract defined in the v304 baseline;
  integration remains deferred. The checker requires both provider message
  identity and authenticated outcome state before reporting implementation
  readiness. Backend acceptance is not represented as confirmed provider
  delivery.

## R008 — Define notification-event retention (P2)

- **Category:** Privacy, database, operations
- **Evidence:** v287 events are durable and preserve audit identity through
  nullable `SET_NULL` references, but no age-based retention or archival policy
  exists.
- **Affected systems:** Notification delivery events, admin, backups, and user
  deletion workflows.
- **User / business value:** Limits unnecessary long-lived notification
  metadata while retaining appropriate support evidence.
- **Technical value:** Bounds table and index growth.
- **Risk if ignored:** Indefinite metadata growth and unclear privacy handling.
- **Effort / implementation risk:** Medium / medium.
- **Dependencies / recommended order:** Legal/product retention decision and
  measured event volume; decide before adding automated deletion.
- **Validation:** Age-boundary, legal-hold if required, audit, and query-plan
  tests.
- **Status:** Retention prerequisites defined in the v304 baseline;
  destructive automation remains deferred. A positive approved duration,
  legal-hold behavior, backup handling and deletion-evidence contract are
  required before cleanup can become implementation-ready.

## R009 — Add a scheduler-level lease if duplicate batch work becomes material (P2)

- **Category:** Performance, operations
- **Evidence:** v287 atomically claims each logical event, so concurrent workers
  cannot normally send the same event, but management commands have no global
  lease and may duplicate candidate matching and audit setup work.
- **Affected systems:** Listing-alert and saved-search schedulers.
- **User / business value:** Reduces wasted database and email-preparation work
  during overlapping schedules.
- **Technical value:** Adds operator-visible single-run coordination without
  replacing event-level correctness.
- **Risk if ignored:** Duplicate scans under scheduler overlap; delivery remains
  protected by v287 claims.
- **Effort / implementation risk:** Small to medium / medium.
- **Dependencies / recommended order:** Measure real overlap first; retain event
  claims as the correctness boundary.
- **Validation:** Concurrent command, lease expiry, crash recovery, and no-send
  regression tests.
- **Status:** Completed in v301. PostgreSQL session advisory locks now
  coordinate listing-price-alert sends and both saved-search scheduler command
  surfaces. Mutating and delivery-capable modes fail closed before candidate
  scanning when the lease is busy; dry-run and read-only report/preview modes
  bypass the lease. Separate database-session concurrency and connection-close
  recovery tests passed. Durable v287 event claims remain the delivery
  correctness boundary.

## R010 — Review recipient data in operator command output (P2)

- **Category:** Privacy, observability
- **Evidence:** New v287-v288 command output is recipient-sanitized, while older
  v221/v223/v224 operator contracts intentionally print addresses and labels.
- **Affected systems:** Saved-search preview, observability, and rollback command
  output plus operational log retention.
- **User / business value:** Reduces accidental exposure in shared terminal or
  centralized logs.
- **Technical value:** Establishes one explicit redaction contract.
- **Risk if ignored:** Recipient addresses may be retained outside the database.
- **Effort / implementation risk:** Small / medium because existing operator
  tests require the current fields.
- **Dependencies / recommended order:** Confirm operator troubleshooting needs
  and log access policy, then update all affected contracts together.
- **Validation:** Redaction, staff workflow, and command snapshot tests.
- **Status:** Completed in v305. All four inventoried explicit-send, preview,
  observability and rollback operator surfaces use one shared idempotent,
  fail-closed redaction helper. Configured addresses render as `[redacted]`,
  unavailable recipients remain `<missing>`, and actual destination values
  remain available only inside the unchanged delivery renderer, sender and
  scheduler contracts. Validation passed 6 focused tests, 1,380 saved-search
  notification tests, 67 policy/delivery compatibility tests and the complete
  2,691-test PostgreSQL parallel regression.

## R011 — Replace sequence-dependent price-alert privacy assertions (P2)

- **Category:** Testing, privacy, maintainability
- **Evidence:** The v285 detail privacy test rejected the buyer's bare numeric
  primary key anywhere in the full HTML response. The same number can
  legitimately appear as a listing ID, layout value, or unrelated markup, so
  suite ordering made the assertion fail without exposing recipient state.
- **Affected systems:** Listing-detail price-alert privacy regression tests.
- **User / business value:** Keeps privacy failures actionable instead of hiding
  them among numeric-substring false positives.
- **Technical value:** Tests the actual exposure boundary: recipient identifiers,
  recipient form fields, and private alert context.
- **Risk if ignored:** Sequence-dependent failures can erode confidence in the
  full regression suite and encourage unsafe test weakening.
- **Effort / implementation risk:** Small / low.
- **Dependencies / recommended order:** None; completed alongside v289 after the
  compatibility batch reproduced the false positive in isolation.
- **Validation:** Isolated v285 test, 53-test notification compatibility batch,
  and the complete 2,511-test regression suite.
- **Status:** Implemented in repair R003; anonymous and private-state privacy
  assertions remain intact.

## R012 — Instrument seller engagement before performance analytics (P2)

- **Category:** Product analytics, privacy, database
- **Evidence:** Listings have price history, favorites, alerts, and messages,
  but the repository has no canonical listing-impression, detail-view, contact,
  or conversion event model. v290 therefore reports only owned asking-price and
  price-history facts.
- **Affected systems:** Seller pricing dashboard, listing detail, analytics, and
  future seller recommendations.
- **User / business value:** Enables evidence-based pricing guidance without
  presenting inferred or misleading performance claims.
- **Technical value:** Establishes explicit event definitions, deduplication,
  retention, and query boundaries before analytics data proliferates.
- **Risk if ignored:** Future dashboards may label favorites or messages as
  views/conversions, or collect behavioral data without a privacy contract.
- **Effort / implementation risk:** Medium to large / medium.
- **Dependencies / recommended order:** Product metric definitions, consent and
  retention policy, bot filtering, and representative query-volume estimates.
- **Validation:** Event-definition contracts, authorization and privacy tests,
  bot/replay deduplication, retention boundaries, and dashboard query plans.
- **Status:** Deferred. Do not add engagement or conversion claims until the
  product and privacy policies above are defined.

## R013 — Define pricing-integrity adjudication before enforcement (P1)

- **Category:** Correctness, security, moderation, operations
- **Evidence:** v293 records sequence-based promotional restrictions and v294
  gives staff a bounded, read-only evidence queue. The repository does not yet
  define review outcomes, who may apply them, seller notice requirements,
  appeal behavior, or how an incorrect flag is reversed without rewriting
  history.
- **Affected systems:** Listing price history, staff moderation, seller notices,
  trust-and-safety audit logs, and future deals surfaces.
- **User / business value:** Enables accountable review without silently
  penalizing sellers or presenting heuristic evidence as a final fraud finding.
- **Technical value:** Establishes one auditable state machine and permission
  boundary before mutable moderation controls are introduced.
- **Risk if ignored:** Ad-hoc enforcement could create inconsistent outcomes,
  weak appeal evidence, or unauthorized listing changes.
- **Effort / implementation risk:** Medium / medium.
- **Dependencies / recommended order:** Define outcomes and seller-facing policy
  before v295 adds any mutable integrity audit workflow.
- **Validation:** Staff authorization, transition-state, concurrent-action,
  audit-log, notification, reversal, and appeal regression tests.
- **Status:** Partially addressed. v294 provides read-only review and v295 adds
  a non-mutating consistency audit. Enforcement and adjudication remain open
  until the product and moderation policy is defined.

## R014 — Add an unapplied-migration deployment preflight (P1)

- **Category:** Correctness, operations, deployment
- **Evidence:** During v295 validation, the migrated Django test database passed
  while the local development database still had listings migrations
  `0019`–`0023` unapplied. The v295 read-only command therefore failed at its
  first query because the expected `reason` column was absent.
- **Affected systems:** Local and production deployment procedures, management
  commands, and schema-dependent background jobs.
- **User / business value:** Prevents runtime failures immediately after code is
  deployed against an older schema.
- **Technical value:** Makes code/schema drift fail early with an actionable
  deployment signal rather than an ORM traceback.
- **Risk if ignored:** Web requests or scheduled jobs may execute new code
  before additive migrations have been applied.
- **Effort / implementation risk:** Small / low.
- **Dependencies / recommended order:** Define whether migration application is
  automatic or operator-controlled, then add `manage.py migrate --check` to the
  deployment/startup preflight without altering data automatically.
- **Validation:** Pending-migration and fully-migrated deployment tests plus a
  documented rollback-safe startup path.
- **Status:** Completed in v302. Production startup now defaults to
  `manage.py migrate --check --noinput` and fails before schema-dependent work
  when committed migrations are unapplied. Local Compose explicitly preserves
  automatic migration application, production application is an
  operator-controlled one-off action, and shell entrypoints are protected by
  repository-enforced LF line endings.
